import logging
from Cusum import Cusum

logger = logging.getLogger('Diagnosis')


class Diagnosis():
    def __init__(self, dbconn):
        self.dbconn = dbconn
        self.sessiontable = self.dbconn.get_table_names()['sessiontable']
        self.summarytable = self.dbconn.get_table_names()['summarytable']
        self.servicestable = self.dbconn.get_table_names()['servicestable']
        self.pingtable = self.dbconn.get_table_names()['pingtable']
        self.tracetable = self.dbconn.get_table_names()['tracetable']

        self.cusumT1 = Cusum('cusumT1')
        self.cusumT2T1 = Cusum('cusumT2T1')
        self.cusumT3T2 = Cusum('cusumT3T2')
        self.cusumTHTTPTTCP = Cusum('cusumTHTTPTTCP')

        self.next_run = []  # contains missing full traces sid.

    # will be loaded from db
    def _load_thresholds(self, url):
        self.thresholds = {}
        for k, v in self.dbconn.get_config().items('diagnosis_threshold'):
            self.thresholds[k] = float(v)

    def get_passive_measurements(self, probeid, url):
        q = '''select a.sid, a.session_start, a.full_load_time, a.page_dim, a.cpu_percent, a.mem_percent, b.sum_http,
        b.sum_tcp, b.tot_obj, b.netw_bytes from {0} a JOIN
        (select sid, session_start, sum(t_http) as sum_http, sum(t_tcp) as sum_tcp, sum(nr_obj) as tot_obj,
        sum(netw_bytes) as netw_bytes from {1} group by sid, session_start) b
        on (a.sid = b.sid and a.session_start = b.session_start) where a.session_url like '%{2}%' and a.probeid = {3}
        order by a.session_start asc;'''.format(self.summarytable, self.servicestable, url, probeid)
        res = self.dbconn.execute_query(q)
        passive = {}
        for tup in res:
            sid = tup[0]
            passive[sid] = {'session_start': tup[1],
                            'full_load_time': tup[2],
                            'page_dim': tup[3],
                            'cpu': tup[4],
                            'mem': tup[5],
                            'http': tup[6],
                            'tcp': tup[7],
                            'nr_obj': tup[8],
                            'netw_bytes': tup[9]
                            }
        return passive

    def get_active_measurements(self, probeid, url, passive):
        active = passive
        for sid, dic in passive.iteritems():
            trace = self.find_complete_trace(sid, dic['session_start'], probeid)
            ping = self.find_ping_values(sid, dic['session_start'], probeid)
            active[sid].update({'trace': trace, 'ping': ping})
        return active

    def find_complete_trace(self, sid, session_start, probeid):
        q = '''select id, hop_nr from {0} where hop_addr = server_ip and sid = {1} and probeid = {2}
        and session_start = '{3}';'''.format(self.tracetable, sid, probeid, session_start)
        res = self.dbconn.execute_query(q)
        try:
            row, hop_nr = res[0]
            q = '''select hop_nr, hop_addr, avg from {0}
            where id <= {1} and id > {1} - {2};'''.format(self.tracetable, row, hop_nr)
            res = self.dbconn.execute_query(q)
            return res
        except IndexError:  # result is empty: no full trace to destination
            self.next_run.append(sid)
            return None


    def find_ping_values(self, sid, sessionstart, probeid):
        q = '''select host, avg from {0} where sid = {1}
        and probeid = {2} and session_start = '{3}';'''.format(self.pingtable, sid, probeid, sessionstart)
        res = self.dbconn.execute_query(q)
        return res

    def get_data_for_url(self, probeid, url):
        passive = self.get_passive_measurements(probeid, url)
        active = self.get_active_measurements(probeid, url, passive)
        return active

    def diagnose_url(self, probeid, url):
        self._load_thresholds(url)
        total = self.get_data_for_url(probeid, url)
        diagnosis = {}
        #['full_load_time', 'netw_bytes', 'session_start', 'trace', 'page_dim', 'mem', 'ping', 'tcp', 'nr_obj', 'http', 'cpu']
        #[ 'netw_bytes', 'session_start', 'trace','ping', 'nr_obj', 'http']
        for sid, v in total.iteritems():
            diagnosis[sid] = ''
            if v['full_load_time'] < self.thresholds['t_th']:
                diagnosis[sid] = 'no problem found. Page load time ok.'
                if sid in self.next_run:
                    self.next_run.remove(sid)
                continue
            if v['cpu'] > self.thresholds['cpu_th'] or v['mem'] > self.thresholds['mem_th']:
                diagnosis[sid] = 'local probe overloaded.'
                if sid in self.next_run:
                    self.next_run.remove(sid)
                continue
            if v['http'] < self.thresholds['http_th']:
                if v['page_dim'] > self.thresholds['dim_th']:
                    diagnosis[sid] = 'page too big'
                elif v['tcp'] > self.thresholds['tcp_th']:
                    diagnosis[sid] = 'web server too far.'
                else:
                    diagnosis[sid] = 'no problem found. Http time ok.'
                if sid in self.next_run:
                    self.next_run.remove(sid)
            else:
                res = self.check_gwlan(probeid, sid)
                if res:
                    diagnosis[sid] = res
                else:
                    diagnosis[sid] = self.check_http_tcp(probeid, v)
        return diagnosis

    def get_hop_nr(self, probeid, sid, hop_nr):
        q = '''select avg from {0} where sid = {1} and hop_nr = {2} and probeid = {3}'''.format(self.tracetable, sid,
                                                                                                hop_nr, probeid)
        res = self.dbconn.execute_query(q)
        return [float(x[0]) for x in res]

    def check_http_tcp(self, probeid, v):
        #probes_on_lan = self.get_probes_on_lan(probeid)
        diff = [v['http'] - v['tcp']]
        if self.cusumTHTTPTTCP.compute(diff):
            return 'remote web server.'
        else:
            return 'generic network (far).'


    def get_probes_on_lan(self, probeid):
        q = '''select distinct probeid from {0} where hop_addr in (select distinct hop_addr from {0} where
        probeid = {1} and hop_nr = 1)'''.format(self.tracetable, probeid)
        res = self.dbconn.execute_query(q)
        return [int(x[0]) for x in res if int(x[0]) != probeid]

    def check_gwlan(self, probeid, sid):
        probes_on_lan = self.get_probes_on_lan(probeid)
        t1hop = self.get_hop_nr(probeid, sid, 1)
        cusum_result = self.cusumT1.compute(t1hop)
        if cusum_result:
            if len(probes_on_lan) > 0:
                return 'LAN congestion'
            else:
                return 'local (LAN/GW) (cusum t1)'
        else:
            t2hop = self.get_hop_nr(probeid, sid, 2)
            t3hop = self.get_hop_nr(probeid, sid, 3)
            if len(probes_on_lan) > 1:
                for p in probes_on_lan:
                    t2hop.extend(self.get_hop_nr(p, sid, 2))
                    t3hop.extend(self.get_hop_nr(p, sid, 3))

            #FIXME
            if len(list(set(t3hop))) == 1 and t3hop[0] == -1:
                #logger.warning('Missing 3rd hop...')
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
                pass
                 #logger.warning('delta2 not computed')
            if self.cusumT2T1.compute(delta1):
                if self.cusumT3T2.compute(delta2):
                    return 'network congestion (cusum delta2)'
                else:
                    return 'gateway problem (cusum delta1)'
            else:
                return 'no problem found. Exclude gw/lan'

if __name__ == "__main__":
    from DBConn import DBConn
    #probeid = 47745875
    #url = '192.168.1.1'
    url = 'nytimes'
    probeid = 410480544
    db = DBConn()
    d = Diagnosis(db)
    di = d.diagnose_url(probeid, url)
    for k, v in di.iteritems():
        print k, ':', v
    #d.check_gwlan(47745875, 1)