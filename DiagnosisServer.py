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
from DBConn import DBConn
import datetime
from datetime import timedelta
from Cusum import Cusum
from DiagnosisStructures import Probe, Ping, Trace, Step
import logging

logger = logging.getLogger('Diagnosis')


class DiagnosisServer():
    def __init__(self, dbconn, clientid, clientip, url):
        self.dbconn = dbconn
        self.thresholds = self._load_thresholds()
        logger.debug('Thresholds loaded.')
        self.applicant = Probe(clientid, clientip, url)
        self.probes = []
        logger.info('Diagnosing (%s) for probe %d' % (url, clientid))
        
    def _load_thresholds(self):
        res = {}
        for (k, v) in self.dbconn.get_config().items('diagnosis_threshold'):
            res[k] = float(v)
        return res
            
    def _add_wildcard_to_addr(self,url):
        if len(url) == 0:
            return '%'
        return '%'+url.strip()+'%'
    
    def save_result(self, sid, result):
        query = '''insert into %s values (now(), %d, %d, '%s','%s')
        ''' % (self.dbconn.get_table_names()['diagnosistable'],self.applicant.get_clientid(), sid, str(self.applicant.get_stats()[str(sid)]['session_start']),result)
        self.dbconn.insert_data_to_db(query)
    
    def get_result(self, time_range):
        tot = []
        applicant_result = self.diagnose_applicant()
        if applicant_result:
            for k in applicant_result.keys():
                self.save_result(int(k), applicant_result[k])
                tot.append(applicant_result)
        else:
            other_result = self.diagnose_lan()
            for k in self.applicant.get_sids():
                self.save_result(k, other_result)
                tot.append({str(k): other_result})
        logger.info('Result: %s', str(tot))
        return tot
   
    def _retrieve_probe_data(self, probe):
        query = '''select distinct on (p.session_start,p.sid) p.* from %s p inner join %s c on (p.clientid = c.clientid) where c.clientid = %d and c.session_url like '%s';
        ''' % (self.dbconn.get_table_names()['clienttable'], self.dbconn.get_table_names()['pingtable'], self.applicant.get_clientid(), self._add_wildcard_to_addr(probe.get_url()))
        local_stats = self.dbconn.execute_query(query)
        for row in local_stats:
            sid = int(row[2])
            probe.add_stat_value(sid, 'session_start', row[3])
            probe.add_stat_value(sid, 't_idle', float(row[4]))
            probe.add_stat_value(sid, 't_tot', float(row[5]))
            probe.add_stat_value(sid, 't_http', float(row[6]))
            probe.add_stat_value(sid, 't_tcp', float(row[7]))
            probe.add_stat_value(sid, 't_dns', float(row[8]))
            probe.add_stat_value(sid, 'cpu_perc', float(row[9]))
            probe.add_stat_value(sid, 'mem_perc', float(row[10]))
            probe.add_stat_value(sid, 'page_dim', int(row[11]))
        query = '''select sid, remoteaddress, step_nr, step_address, rtt_avg from %s where clientid = %d and 
        remoteaddress in (select remoteaddress from %s where session_url like '%s' and clientid = %d);
        ''' % (self.dbconn.get_table_names()['tracetable'], probe.get_clientid(), self.dbconn.get_table_names()['pingtable'], self._add_wildcard_to_addr(probe.get_url()), probe.get_clientid())
        local_trace = self.dbconn.execute_query(query)
        for row in local_trace:
            sid = row[0]
            s = Step(int(row[2]), row[3], float(row[4]))
            if sid in probe.get_traces().keys():
                probe.get_traces()[sid].append(s)
            else:
                traces = {}
                trace = Trace(self.applicant.get_clientid(), row[1], int(row[0]))
                traces[sid] = [s]       
                probe.set_trace(traces)
        query = '''select sid, remoteaddress, ping_min, ping_max, ping_avg, ping_std from %s where clientid = %d and session_url like '%s';
        ''' % (self.dbconn.get_table_names()['pingtable'], probe.get_clientid(), self._add_wildcard_to_addr(probe.get_url()))
        local_ping = self.dbconn.execute_query(query)
        for row in local_ping:
            sid = row[0]
            p = Ping(row[1], float(row[2]), float(row[3]), float(row[4]), float(row[5]))
            probe.add_ping(int(sid), p)
            
            
    def diagnose_applicant(self):
        self._retrieve_probe_data(self.applicant)
        time_th = float(self.thresholds['t_th'])
        cpu_th = float(self.thresholds['cpu_th'])
        http_th = float(self.thresholds['http_th'])
        dim_th = float(self.thresholds['dim_th'])
        tcp_th = float(self.thresholds['tcp_th'])
        dns_th = float(self.thresholds['dns_th'])
        
        stats = self.applicant.get_stats() 
        ##['mem_perc', 't_idle', 'session_start', 't_http', 'page_dim', 't_tcp', 't_dns', 't_tot', 'cpu_perc']
        results = {}
        for sid in stats.keys():
            stat = stats[sid]
            if (float(stat['t_idle'] / stat['t_tot']) > time_th) or (stat['cpu_perc'] > cpu_th):
                results[sid] = 'local client'
            if stat['t_http'] < http_th:
                if stat['page_dim'] > dim_th:
                    results[sid] = 'page too big'
                if stat['t_tcp'] > tcp_th:
                    results[sid] = 'web server too far'
                if stat['t_dns'] > dns_th:
                    results[sid] = 'dns problem'
            else:
                results[sid] = None
        
        return results
        
    def _get_gw(self):
        query = '''select distinct on (step_address) step_address from %s where clientid = %d and step_nr = 1;
        ''' % (self.dbconn.get_table_names()['tracetable'], self.applicant.get_clientid())
        res = self.dbconn.execute_query(query)
        assert len(res) == 1
        return res[0][0]
    
    def __get_probes_on_lan(self, gw):
        query = '''select distinct on (clientid) clientid from %s where clientid != %d and step_nr = 1 and step_address = '%s';
        ''' % (self.dbconn.get_table_names()['tracetable'], self.applicant.get_clientid(), gw)
        res = self.dbconn.execute_query(query)
        probes_on_lan = [int(r[0]) for r in res]
        if len(probes_on_lan) == 0:
            return 'all', probes_on_lan
        tmp = str(probes_on_lan).replace("[","(").replace("]",")")
        query = '''select result from %s where clientid in %s;
        ''' % (self.dbconn.get_table_names()['diagnosistable'], tmp)
        res = self.dbconn.execute_query(query)
        if len(res) == len(probes_on_lan) - 1: #remove the applicant
            return 'all', probes_on_lan
        elif len(res) == 0:
            return 'none', probes_on_lan
        else:
            return 'some', probes_on_lan
    
    
    def __get_rtt_hop(self, probe, hop_nr):
        hop_rtt = []
        for sid in probe.get_traces().keys():
            hop_rtt.extend([s.get_rtt_step() for s in probe.get_traces()[sid] if s.get_step_nr() == hop_nr])
        return hop_rtt
    
    def _get_thttp_minus_ttcp(self, probe):
        diff = []
        for sid in probe.get_stats().keys():
            diff.append( probe.get_stats()[sid]['t_http'] - probe.get_stats()[sid]['t_tcp'])
        return diff
    
    def check_gw_lan(self, probes):
        t1hop = self.__get_rtt_hop(self.applicant, 1)
        cusum = Cusum()
        cusum_result = cusum.compute(t1hop)
        diagnosis = '0'
        if cusum_result:
            diagnosis = 'gw'
            for p in probes:
                p1hop = self.__get_rtt_hop(p, 1)
                if cusum.compute(p1hop):
                    diagnosis = 'lan congestion'
            cs_new = cusum.adjust_th(cusum_result)
            if cs_new > -1:
                logger.info('Cusum threshold changed to: %s' % str(cs_new))
        else:
            t2hop = self.__get_rtt_hop(self.applicant, 2)
            t3hop = self.__get_rtt_hop(self.applicant, 3)
            for p in probes:
                p2hop = self.__get_rtt_hop(p, 2)
                p3hop = self.__get_rtt_hop(p, 3)
                t2hop.extend(p2hop)
                t3hop.extend(p3hop)
                
            delta1 = [x-y for x,y in zip(t2hop, t1hop)]
            delta2 = [x-y for x,y in zip(t3hop, t2hop)]
            
            if cusum.compute(delta1):
                if cusum.compute(delta2):
                    diagnosis = 'lan congestion'
                else:
                    diagnosis = 'gw'
        
        return diagnosis
    
    def check_http_tcp(self, probes):
        diff = self._get_thttp_minus_ttcp(probes)
        diff.extend(self._get_thttp_minus_ttcp(self.applicant))
        c = Cusum()
        if c.compute(diff):
            return 'remote web server'
        else:
            return 'network'
        
    def diagnose_lan(self):
        diagnosis = ''
        gw = self._get_gw()
        res, id_probes_on_lan = self.__get_probes_on_lan(gw)
        probes = []
        for probeid in id_probes_on_lan:
            p = Probe(probeid)
            self._retrieve_probe_data(p)
            probes.append(p)
        
        #print 'probes: ', probes
        if res == 'all':
            return self.check_gw_lan(probes)
        elif res == 'none':
            return self.check_http_tcp(probes)
        else:
            return 'generic network'
        

if __name__ == '__main__':
    db = DBConn()
    db.create_tables()
    url = 'www.google.com'
    clientid = 453982341
    clientip = '127.0.0.1'
    d = DiagnosisServer(db, clientid, clientip, url)
    print d.get_result(6)
