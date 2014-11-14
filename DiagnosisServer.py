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
import logging
import Utils
from DBConn import DBConn
from Cusum import Cusum
from DiagnosisStructures import Probe, Ping, Trace, Step
import json


logger = logging.getLogger('Diagnosis')


class DiagnosisServer():
    def __init__(self, dbconn, clientid, clientip):
        self.dbconn = dbconn
        self.applicant = Probe(clientid, clientip)
        self.sessiontable = self.dbconn.get_table_names()['sessiontable']
        self.summarytable = self.dbconn.get_table_names()['summarytable']
        self.servicestable = self.dbconn.get_table_names()['servicestable']
        self.pingtable = self.dbconn.get_table_names()['pingtable']
        self.tracetable = self.dbconn.get_table_names()['tracetable']
        self.testsid = 0  # TODO: fa cagare

        thresholds = self._load_thresholds()
        self.time_th = float(thresholds['t_th'])
        self.cpu_th = float(thresholds['cpu_th'])
        self.http_th = float(thresholds['http_th'])
        self.dim_th = float(thresholds['dim_th'])
        self.tcp_th = float(thresholds['tcp_th'])
        self.dns_th = float(thresholds['dns_th'])
        logger.debug('Thresholds for local stats loaded.')

        self.probes_on_lan = []
        logger.info("Diagnosis running for probe {0}".format(self.applicant.get_clientid()))
        
    def _load_thresholds(self):
        res = {}
        for (k, v) in self.dbconn.get_config().items('diagnosis_threshold'):
            res[k] = float(v)
        return res

    # to add: limit diagnosis in a certain time range
    def do_diagnosis(self, url, time_range=6):
        self._retrieve_probe_data(self.applicant, url)
        applicant_result = self.diagnose_applicant()
        for sid, result in applicant_result.iteritems():
            if sid > self.testsid:
                self.save_result(int(sid), result)
        logger.info("Result saved: {0} sessions for probe {1}".format(len(applicant_result.keys()),
                                                                      self.applicant.get_clientid()))

    def save_result(self, sid, result):
        query = '''insert into {0} values (now(), {1}, {2}, '{3}','{4}')
        '''.format(self.dbconn.get_table_names()['diagnosistable'], self.applicant.get_clientid(), sid,
                   str(self.applicant.get_stats()[str(sid)]['session_start']), result)
        self.dbconn.insert_data_to_db(query)

    def _retrieve_probe_data(self, probe, url):
        logger.debug("Diagnosing {0}".format(url))
        query = '''select a.sid, a.session_start, a.full_load_time, a.page_dim, a.cpu_percent, a.mem_percent,
        b.sum_http, b.sum_tcp from {0} a JOIN
        (select sid, session_start, sum(t_http) as sum_http, sum(t_tcp) as sum_tcp
        from {1} group by sid, session_start) b
        on (a.sid = b.sid and a.session_start = b.session_start)
        where a.session_url like '{2}' and a.probeid = {3};'''.format(self.summarytable, self.servicestable,
                                                                      Utils.add_wildcard_to_url(url),
                                                                      self.applicant.get_clientid())


        local_stats = self.dbconn.execute_query(query)
        #print local_stats
        #exit()
        involved_sids = []
        for row in local_stats:
            sid = int(row[0])
            involved_sids.append(sid)
            probe.add_stat_value(sid, 'session_start', row[1])
            #probe.add_stat_value(sid, 't_idle', float(row[2]))
            probe.add_stat_value(sid, 't_tot', float(row[2]))
            probe.add_stat_value(sid, 'page_dim', int(row[3]))
            probe.add_stat_value(sid, 'cpu_perc', int(row[4]))
            probe.add_stat_value(sid, 'mem_perc', int(row[5]))
            probe.add_stat_value(sid, 't_http', int(row[6]))
            probe.add_stat_value(sid, 't_tcp', int(row[7]))
            #probe.add_stat_value(sid, 't_dns', float(row[6]))

        if len(involved_sids) == 1:
            tuple_involved = '( %d )' % involved_sids[0]
        else:
            tuple_involved = str(tuple(involved_sids))

        query = '''select sid, server_ip, hop_nr, hop_addr, avg from %s where probeid = %d and sid in %s
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

        query = '''select sid, host, min, max, avg, std, loss from %s where probeid = %d and sid in %s;
        ''' % (self.dbconn.get_table_names()['pingtable'], probe.get_clientid(), tuple_involved)
        local_ping = self.dbconn.execute_query(query)
        for row in local_ping:
            sid = row[0]
            p = Ping(sid, row[1], float(row[2]), float(row[3]), float(row[4]), float(row[5]), int(row[6]))
            probe.add_ping(sid, p)

    def diagnose_applicant(self):
        results = {}
        stats = self.applicant.get_stats()
        logger.info('applicant stats: (%d) sids involved' % (len(stats.keys())))
        ordered_sids = Utils.order_numerical_keys(stats)
        for sid in ordered_sids:
            stat = stats[sid]
            #if (float(stat['t_idle'] / stat['t_tot']) > self.time_th) or (stat['cpu_perc'] > self.cpu_th):
            if stat['cpu_perc'] > self.cpu_th:
                #results[sid] = 'local client: %s' % ('t_idle/t_tot > %.2f' % self.time_th if (float(stat['t_idle'] / stat['t_tot']) > self.time_th) else 'cpu_perc > %.2f' % self.cpu_th)
                results[sid] = 'local client: %s' % ('cpu_perc > %.2f' % self.cpu_th)
                logger.debug('sid %s = %s' % (sid, results[sid]))
                continue
            if stat['t_http'] < self.http_th:
                if stat['page_dim'] > self.dim_th:
                    results[sid] = 'page too big: page_dim > %.2f' % self.dim_th
                elif stat['t_tcp'] > self.tcp_th:
                    results[sid] = 'web server too far: t_tcp > %.2f' % self.tcp_th
                #elif stat['t_dns'] > self.dns_th:
                #    results[sid] = 'dns problem: t_dns > %.2f' % dns_th
                else:
                    results[sid] = 0
                logger.debug('sid %s = %s' % (sid, results[sid]))
                continue
            else:
                logger.debug('sid: %s = t_http > %.2f: checking gw - lan' % (sid, self.http_th))
                gw_lan = self.diagnose_gw_lan(sid, url)
                results[sid] = gw_lan
                logger.debug('sid %s = %s' % (sid, results[sid]))
                continue
            logger.debug('sid %s = %s' % (sid, results[sid]))
        return results

    #
    def diagnose_gw_lan(self, sid, url):
        diagnosis = None
        gw = self._get_gw()
        logger.debug('Gateway: %s' % gw)
        t1hop = self._get_rtt_hop_nr(self.applicant, 1, sid)
        #logger.debug('hop to gw: %s - %d' % (str(t1hop), len(t1hop)))
        self.probes_on_lan = self._get_probes_on_lan(gw)
        logger.debug('found %d probes using gateway: %s' % (len(self.probes_on_lan), gw))
        cusumT1 = Cusum('cusumT1')
        cusum_result = cusumT1.compute(t1hop)
        #FIXME
        l1hop = self._get_loss_rate_hop_nr(self.applicant, 1, sid)

        if cusum_result:
            logger.debug('cusum computed on 1st hop (gw)')
            diagnosis = 'local (LAN/GW)'

            #count = 0
            #if len(self.probes_on_lan) > 1:
            # TODO: ask probe to ping other probes on lan (supervisor)
            # cusumTP
                #pass
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


            #FIXME
            if len(list(set(t3hop))) == 1 and t3hop[0] == -1:
                logger.warning('Missing 3rd hop...')
                t3hop = [2 * x for x in t2hop]
            else:
                if (min(t3hop)) == -1:
                    for n, i in enumerate(t3hop):
                        if i == -1:
                            t3hop[n] = t2hop[n] * 2
            #EOFIXME

            delta1 = [x-y for x, y in zip(t2hop, t1hop)]
            delta2 = []
            try:
                delta2 = [x-y for x, y in zip(t3hop, t2hop)]
            except:
                 logger.warning('delta2 not computed')

            logger.debug("delta1: {0}".format(delta1))
            logger.debug("delta2: {0}".format(delta2))
            cusumT2T1 = Cusum('cusumT2T1')
            if cusumT2T1.compute(delta1):
                logger.debug('cusum computed on t2 - t1')
                cusumT3T2 = Cusum('cusumT3T2')
                if cusumT3T2.compute(delta2):
                    logger.debug('cusum computed on t3 - t2')
                    diagnosis = 'network (cusum on t3 and t2)'
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

    # need to update the probe here: ping to step 1, 2, 3 and destination.
    def _get_loss_rate_hop_nr(self, probe, hop, current_sid):
        pass

    def _get_gw(self):
        query = '''select distinct on (hop_addr) hop_addr from %s where probeid = %d and hop_nr = 1 and sid > %d;
        ''' % (self.dbconn.get_table_names()['tracetable'], self.applicant.get_clientid(), self.testsid)
        res = self.dbconn.execute_query(query)
        assert len(res) == 1
        return res[0][0]

    def _get_probes_on_lan(self, gw):
        query = '''select distinct on (probeid) probeid from %s where hop_nr = 1 and hop_addr = '%s' and sid > %d;
        ''' % (self.dbconn.get_table_names()['tracetable'], gw, self.testsid)
        res = self.dbconn.execute_query(query)
        probes = [int(r[0]) for r in res]
        if len(probes) == 1 and probes[0] == self.applicant.get_clientid():
            logger.debug('%d is the only known probe on its LAN' % self.applicant.get_clientid())
        return probes

    def _get_thttp_minus_ttcp(self, probes_on_lan, sid):
        diff = []
        #if sid in probe.get_stats().keys():
        if sid in self.applicant.get_stats().keys():
        #for sid in probe.get_stats().keys():
            #diff.append(probe.get_stats()[sid]['t_http'] - probe.get_stats()[sid]['t_tcp'])
            diff.append(self.applicant.get_stats()[sid]['t_http'] - self.applicant.get_stats()[sid]['t_tcp'])
            return diff
        else:
            logger.error('Unable to find sid {0} for probe {1}'.format(sid, self.applicant.get_clientid()))
            return None

    def check_http_tcp(self, sid):
        diff = self._get_thttp_minus_ttcp(self.probes_on_lan, sid)
        if not diff:
            logger.error('Poi decido')
            return 'network generic: unable to get more details'
        c = Cusum('cusumTHTTPTTCP')
        if c.compute(diff):
            return 'remote web server'
        else:
            # TODO in use case: return network generic as user has clicked
            return 'no problem found: unable to get more details'

    def get_counter(self):
        return self.counter

    def get_destination_ip(self, url):
        q = '''select distinct max(sid), remoteaddress from %s where clientid = %d and session_url = '%s'
        group by remoteaddress ''' % (self.dbconn.get_table_names()['pingtable'],
                                      self.applicant.get_clientid(), url)
        res = self.dbconn.execute_query(q)
        max_sid = max(list(set([x[0] for x in res])))
        ip_addresses = [x[1] for x in res if x[0] == max_sid]
        q = '''select step_address from %s
        where sid = %d and step_nr in (select max(step_nr) from %s where clientid = %d and sid = %d and remoteaddress in %s);
        ''' % (self.dbconn.get_table_names()['tracetable'], max_sid, self.dbconn.get_table_names()['tracetable'],
            self.applicant.get_clientid(), max_sid, tuple(ip_addresses))
        res = self.dbconn.execute_query(q)
        destination_ip = res[0][0]
        logger.info('Found destination IP for url %s: %s' % (url, destination_ip))
        return destination_ip

    def import_data(self):
        data = {}
        q = '''select a.probeid, a.probeip, a.sid, a.session_url, a.session_start, a.server_ip, a.full_load_time,
        a.page_dim, a.cpu_percent, a.mem_percent, a.services, a.active_measurements
        from {0} a
        LEFT JOIN {1} b on (a.sid = b.sid and a.probeid = b.probeid and a.session_start = b.session_start)
        where b.sid is NULL;
        '''.format(self.sessiontable, self.summarytable)
        res = self.dbconn.execute_query(q)
        for measure in res:
            data[measure[2]] = {'probeid': measure[0],
                                'probeip': measure[1],
                                'session_url': measure[3],
                                'session_start': measure[4],
                                'server_ip': measure[5],
                                'full_load_time': measure[6],
                                'page_dim': measure[7],
                                'cpu_percent': measure[8],
                                'mem_percent': measure[9],
                                'services': json.loads(measure[10]),
                                'active_measurements': json.loads(measure[11])}

        logger.info("Fetched {0} new sessions from the db".format(len(data)))

        for sid, session in data.iteritems():
            q = '''insert into {0} (probeid, probeip, sid, session_url, session_start, server_ip, full_load_time,
            page_dim, cpu_percent,mem_percent ) values
            ({1}, '{2}', {3}, '{4}', '{5}', '{6}', {7}, {8}, {9}, {10})'''.format(self.summarytable, session['probeid'],
                                                                                  session['probeip'], sid,
                                                                                  session['session_url'],
                                                                                  session['session_start'],
                                                                                  session['server_ip'],
                                                                                  session['full_load_time'],
                                                                                  session['page_dim'],
                                                                                  session['cpu_percent'],
                                                                                  session['mem_percent'])
            self.dbconn.insert_data_to_db(q)

            for service in session['services']:
                q1 = '''insert into {0} (probeid, sid, session_url, session_start, service_base_url, service_ip,
                netw_bytes, t_tcp, t_http, rcv_time, nr_obj) values ({1}, {2}, '{3}', '{4}', '{5}', '{6}', {7}, {8},
                {9}, {10}, {11})'''.format(self.servicestable, session['probeid'], sid, session['session_url'],
                                           session['session_start'], service['base_url'], service['ip'],
                                           service['netw_bytes'], service['sum_syn'], service['sum_http'],
                                           service['sum_rcv_time'], service['nr_obj'])

                self.dbconn.insert_data_to_db(q1)

            for ip, active_measure in session['active_measurements'].iteritems():
                ping = json.loads(active_measure['ping'])
                trace = json.loads(active_measure['trace'])

                q2 = '''insert into {0} (probeid, sid, session_start, server_ip, host, min, max, avg, std, loss) values
                ({1}, {2}, '{3}', '{4}', '{5}', {6}, {7}, {8}, {9}, {10})'''.format(self.pingtable, session['probeid'],
                                                                                    sid, session['session_start'],
                                                                                    session['server_ip'], ping['host'],
                                                                                    ping['min'], ping['max'],
                                                                                    ping['avg'], ping['std'],
                                                                                    ping['loss'])

                self.dbconn.insert_data_to_db(q2)

                for step in trace:
                    rtt = step['rtt']
                    if rtt == -1:
                        q3 = '''insert into {0} (probeid, sid, session_start, server_ip, hop_nr, min, max, avg,
                        std, endpoints) values ({1}, {2}, '{3}', '{4}', {5}, {6}, {7},
                        {8}, {9}, '{10}')'''.format(self.tracetable, session['probeid'], sid, session['session_start'],
                                                    session['server_ip'], step['hop_nr'], -1, -1, -1, -1,
                                                    json.dumps(step['endpoints']))
                    else:
                        q3 = '''insert into {0} (probeid, sid, session_start, server_ip, hop_addr, hop_nr, min, max,
                        avg, std, endpoints) values ({1}, {2}, '{3}', '{4}', '{5}', {6}, {7}, {8}, {9}, {10}, '{11}')
                        '''.format(self.tracetable, session['probeid'], sid, session['session_start'],
                                   session['server_ip'], step['ip_addr'], step['hop_nr'], rtt['min'], rtt['max'],
                                   rtt['avg'], rtt['std'], json.dumps(step['endpoints']))

                    self.dbconn.insert_data_to_db(q3)

        logger.info("Session(s) successfully imported.")

if __name__ == '__main__':
    #import sys
    import logging.config
    logging.config.fileConfig('logging.conf')
    logger = logging.getLogger('Diagnosis')

    url = 'http://www.google.com/'
    clientid = 1650603488
    clientip = '127.0.0.1'

    db = DBConn()
    d = DiagnosisServer(db, clientid, clientip)
    #d.import_data()
    d.do_diagnosis(url)
