from collections import namedtuple

class Reasoner():
    
    def __init__(self, dic, url):
        self.sessions_list = dic
        self.url = url

    def _process_passive(self, dic):
        passive = namedtuple('passive', ['probe_id', 'sid', 'server_ip', 'session_start', 'full_load_time', 'page_dim', 'mem_percent', 'cpu_percent'])
        passive.sid = dic['sid']
        passive.probe_id = dic['probe_id']
        passive.server_ip = dic['server_ip']
        passive.session_start = dic['session_start']
        passive.full_load_time = dic['full_load_time']
        passive.page_dim = dic['page_dim']
        passive.mem_percent = dic['mem_percent']
        passive.cpu_percent = dic['cpu_percent']
        return passive

    def _process_active(dicping, dictrace):
        pass

    def _process_secondary(secondarylist):
        #{'secondary_base_url': 'http://i.po.st', 'secondary_nr_obj': 1, 'secondary_ip': '8.254.173.126', 'secondary_sum_http': 27, 'secondary_sum_syn': 27, 'secondary_netw_bytes': 118589, 'secondary_sum_rcv_time': 205}
        pass
        
        
    def gather_measurements(self):
        session = self.sessions_list[0].__dict__
        passive = self._process_passive(session['other'])
        secondary = session['secondary']
        ping = session['ping']
        trace = session['trace']
        print(trace)
        #for session in self.sessions_list:
            #session dict_keys(['secondary', 'local_diagnosis', 'ping', '_check', 'trace', 'attributes', 'location', 'other'])
         
            
        
    def diagnose(self):
        self.gather_measurements()
            
            
