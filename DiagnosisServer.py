#!/usr/bin/python
#
# mPlane QoE Server
#
# (c) 2013-2014 mPlane Consortium (http://www.ict-mplane.eu)
#               Author: Marco Milanesio <milanesio.marco@gmail.com>
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <http://www.gnu.org/licenses/>.
#
import datetime
import logging
import Utils
from datetime import timedelta
from DBConn import DBConn
from Cusum import Cusum
from DiagnosisStructures import Probe, Ping, Trace, Step

logger = logging.getLogger('Diagnosis')


class DiagnosisServer():
    def __init__(self, dbconn, clientid, clientip, url):
        self.url = url
        self.destination_ip = self.get_destination_ip()
        self.dbconn = dbconn
        thresholds = self._load_thresholds()
        self.time_th = float(thresholds['t_th'])
        self.cpu_th = float(thresholds['cpu_th'])
        self.http_th = float(thresholds['http_th'])
        self.dim_th = float(thresholds['dim_th'])
        self.tcp_th = float(thresholds['tcp_th'])
        self.dns_th = float(thresholds['dns_th'])
        logger.debug('Thresholds loaded.')
        self.applicant = Probe(clientid, clientip)
        self._retrieve_probe_data(self.applicant)
        logger.info('Diagnosing (%s) for probe %d' % (self.url, self.applicant.get_clientid()))
        
    def _load_thresholds(self):
        res = {}
        for (k, v) in self.dbconn.get_config().items('diagnosis_threshold'):
            res[k] = float(v)
        return res

    # to add: limit diagnosis in a certain time range
    def do_diagnosis(self, time_range=6):
        applicant_result = self.diagnose_applicant()
        for sid, result in applicant_result.iteritems():
            self.save_result(int(sid), result)
        logger.info('Result saved: %d sessions for probe %d' % (len(applicant_result.keys()), self.applicant.get_clientid()))
    
    def save_result(self, sid, result):
        query = '''insert into %s values (now(), %d, %d, '%s','%s')
        ''' % (self.dbconn.get_table_names()['diagnosistable'],self.applicant.get_clientid(), sid, str(self.applicant.get_stats()[str(sid)]['session_start']),result)
        self.dbconn.insert_data_to_db(query)

    def _retrieve_probe_data(self, probe):
        query = '''select sid, session_start, t_idle, t_tot, t_http, t_tcp, t_dns, cpu_perc, mem_perc, page_dim from %s where sid in (select distinct sid from %s where session_url like '%s' and clientid = %d);
        ''' % (self.dbconn.get_table_names()['clienttable'], self.dbconn.get_table_names()['pingtable'], Utils.add_wildcard_to_url(self.url), self.applicant.get_clientid())
        local_stats = self.dbconn.execute_query(query)
        involved_sids = []
        for row in local_stats:
            sid = int(row[0])
            involved_sids.append(sid)
            probe.add_stat_value(sid, 'session_start', row[1])
            probe.add_stat_value(sid, 't_idle', float(row[2]))
            probe.add_stat_value(sid, 't_tot', float(row[3]))
            probe.add_stat_value(sid, 't_http', float(row[4]))
            probe.add_stat_value(sid, 't_tcp', float(row[5]))
            probe.add_stat_value(sid, 't_dns', float(row[6]))
            probe.add_stat_value(sid, 'cpu_perc', float(row[7]))
            probe.add_stat_value(sid, 'mem_perc', float(row[8]))
            probe.add_stat_value(sid, 'page_dim', int(row[9]))
        
        if len(involved_sids) == 1:
            tuple_involved = '( %d )' % involved_sids[0]
        else:
            tuple_involved = str(tuple(involved_sids))
        
        query = '''select sid, remoteaddress, step_nr, step_address, rtt_avg from %s where clientid = %d and sid in %s
        ''' % (self.dbconn.get_table_names()['tracetable'], probe.get_clientid(), tuple_involved)
        local_trace = self.dbconn.execute_query(query)
        
        tot = {}
        for sid in involved_sids:
            traces = {}
            tmp = [x for x in local_trace if x[0] == sid]
            for tup in tmp:
                if tup[1] not in traces.keys():
                    t = Trace(tup[1])
                else:
                    t = traces[tup[1]]
                s = Step(tup[2], tup[3], tup[4])
                t.add_step(s)
                traces.update({tup[1]: t})
            tot[str(sid)] = traces
            
        #for k,v in traces['192.168.1.1'].get_steps().iteritems():
        #    print k, v.get_step_address()
        #for k, v in tot.iteritems():
        #    print k, v
        #    for i, j in v.iteritems():
        #        print i, len(j.get_steps())
        for sid, tr in tot.iteritems():
            for target, trace in tr.iteritems():
                probe.add_trace(sid, trace)
        
        query = '''select sid, remoteaddress, ping_min, ping_max, ping_avg, ping_std from %s where clientid = %d and sid in %s;
        ''' % (self.dbconn.get_table_names()['pingtable'], probe.get_clientid(), tuple_involved)
        local_ping = self.dbconn.execute_query(query)
        for row in local_ping:
            sid = row[0]
            p = Ping(sid, row[1], float(row[2]), float(row[3]), float(row[4]), float(row[5]))
            probe.add_ping(sid, p)

    def diagnose_applicant(self):
        results = {}
        stats = self.applicant.get_stats()
        logger.info('applicant stats: (%d) sids involved' % (len(stats.keys())))
        ordered_sids = Utils.order_numerical_keys(stats)
        for sid in ordered_sids:
            stat = stats[sid]
            if (float(stat['t_idle'] / stat['t_tot']) > self.time_th) or (stat['cpu_perc'] > self.cpu_th):
                results[sid] = 'local client: %s' % ('t_idle/t_tot > %.2f' % self.time_th if (float(stat['t_idle'] / stat['t_tot']) > self.time_th) else 'cpu_perc > %.2f' % self.cpu_th)
                logger.debug('sid %s = %s' % (sid, results[sid]))
                continue
            if stat['t_http'] < self.http_th:
                if stat['page_dim'] > self.dim_th:
                    results[sid] = 'page too big: page_dim > %.2f' % self.dim_th
                elif stat['t_tcp'] > self.tcp_th:
                    results[sid] = 'web server too far: t_tcp > %.2f' % self.tcp_th
                elif stat['t_dns'] > self.dns_th:
                    results[sid] = 'dns problem: t_dns > %.2f' % dns_th
                else:
                    results[sid] = 0
                logger.debug('sid %s = %s' % (sid, results[sid]))
                continue
            else:
                logger.debug('sid: %s = t_http > %.2f: checking gw - lan' % (sid, self.http_th))
                gw_lan = self.diagnose_gw_lan(sid)
                results[sid] = gw_lan
                logger.debug('sid %s = %s' % (sid, results[sid]))
                continue
            logger.debug('sid %s = %s' % (sid, results[sid]))
        return results

    def diagnose_gw_lan(self, sid):
        diagnosis = None
        gw = self._get_gw()
        logger.debug('Gateway: %s' % gw)
        t1hop = self._get_rtt_hop_nr(self.applicant, 1, sid)
        #logger.debug('hop to gw: %s - %d' % (str(t1hop), len(t1hop)))
        self.probes_on_lan = self._get_probes_on_lan(gw)
        logger.debug('found %d probes using gateway: %s' % (len(self.probes_on_lan), gw))
        cusumT1 = Cusum('cusumT1')
        cusum_result = cusumT1.compute(t1hop)
        if cusum_result:
            logger.debug('cusum computed on 1st hop (gw)')
            diagnosis = 'local (LAN/GW)'

            count = 0
            if len(self.probes_on_lan) > 1:
            # TODO: ask probe to ping other probes on lan (supervisor)
            # cusumTP
                pass
                # NON ANCORA
                #cs_new = cusum.adjust_th(cusum_result)
                #logger.info('Cusum threshold changed to: %s' % str(cs_new))

        else:
            t2hop = self._get_rtt_hop_nr(self.applicant, 2, sid)
            t3hop = self._get_rtt_hop_nr(self.applicant, 3, sid)
            if len(self.probes_on_lan) > 1:
                for p in self.probes_on_lan:
                    t2hop.extend(self._get_rtt_hop_nr(p, 2, sid))
                    t3hop.extend(self._get_rtt_hop_nr(p, 3, sid))
                
            delta1 = [x-y for x, y in zip(t2hop, t1hop)]
            delta2 = [x-y for x, y in zip(t3hop, t2hop)]
            logger.debug('delta1: ', str(delta1))
            logger.debug('delta2: ', str(delta2))
            cusumT2T1 = Cusum('cusumT2T1')
            if cusumT2T1.compute(delta1):
                logger.debug('cusum computed on t2 - t1')
                cusumT3T2 = Cusum('cusumT3T2')
                if cusumT3T2.compute(delta2):
                    logger.debug('cusum computed on t3 - t2: lan congestion')
                    diagnosis = 'lan congestion (cusum on t3-t2-t1)'
                else:
                    logger.debug('only t2 - t1: gw')
                    diagnosis = 'gw (cusum on t2-t1)'

        if not diagnosis:
            diagnosis = self.check_http_tcp(sid)
        return diagnosis

    def _get_rtt_hop_nr(self, probe, hop, current_sid):
        res = []
        for sid, trace_list in probe.get_traces().iteritems():
            if sid == current_sid:
                for trace in trace_list:
                    res.append(float(trace.get_step_number(hop).get_rtt()))
        return res
        
    def _get_gw(self):
        query = '''select distinct on (step_address) step_address from %s where clientid = %d and step_nr = 1;
        ''' % (self.dbconn.get_table_names()['tracetable'], self.applicant.get_clientid())
        res = self.dbconn.execute_query(query)
        assert len(res) == 1
        return res[0][0]
    
    def _get_probes_on_lan(self, gw):
        probes = []
        #query = '''select distinct on (clientid) clientid from %s where clientid != %d and step_nr = 1 and step_address = '%s';
        #''' % (self.dbconn.get_table_names()['tracetable'], self.applicant.get_clientid(), gw)
        
        query = '''select distinct on (clientid) clientid from %s where step_nr = 1 and step_address = '%s';
        ''' % (self.dbconn.get_table_names()['tracetable'], gw)
        res = self.dbconn.execute_query(query)
        probes = [int(r[0]) for r in res]
        if len(probes) == 1 and probes[0] == self.applicant.get_clientid():
            logger.debug('%d is the only known probe on its LAN' % self.applicant.get_clientid())
        return probes

    def _get_thttp_minus_ttcp(self, probe, sid):
        diff = []
        if sid in probe.get_stats().keys():
        #for sid in probe.get_stats().keys():
            diff.append(probe.get_stats()[sid]['t_http'] - probe.get_stats()[sid]['t_tcp'])
            return diff
        else:
            logger.error('Unable to find sid {0} for probe {1}'.format(sid, probe.get_clientid()))
            return None
    
    def check_http_tcp(self, sid):
        diff = self._get_thttp_minus_ttcp(self.probes, sid)
        if not diff:
            logger.error('Poi decido')
            return 'network generic: unable to get more details'
        c = Cusum('cusumTHTTPTTCP')
        if c.compute(diff):
            return 'remote web server'
        else:
            return 'network'

    def get_counter(self):
        return self.counter

    def get_destination_ip(self):
        q = '''select distinct step_address from trace_20141008
        where step_nr in (select max(step_nr) from trace_20141008 where sid = 1);
        '''
        return '192.168.1.1'
        pass


if __name__ == '__main__':
    #import sys
    import logging.config
    logging.config.fileConfig('logging.conf')
    logger = logging.getLogger('Diagnosis')

    url = ''
    clientid = 1478414590
    clientip = '131.114.54.80'

    db = DBConn()
    d = DiagnosisServer(db, clientid, clientip, url)
    d.do_diagnosis()

    #if d.get_counter() < 1000:
    #    d.update_thresholds()
    #else:
    #    d.do_diagnosis()
    #d.get_result(6)
