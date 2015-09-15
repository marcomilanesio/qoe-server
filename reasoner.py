from collections import namedtuple
from diagnosis import DiagnosisManager

dbname = 'reasoner.db'


class Reasoner:
    
    def __init__(self, dic, url):
        self.sessions_list = dic
        self.url = url
        self.dm = DiagnosisManager(dbname, self.url)

    @staticmethod
    def _process_passive(dic):
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

    def gather_measurements(self):
        measurements = []
        metric = namedtuple('metrics', ['passive', 'ping', 'trace', 'secondary'])
        session = self.sessions_list[0].__dict__
        passive = Reasoner._process_passive(session['other'])
        secondary = session['secondary']
        ping = session['ping']
        trace = session['trace']
        metric.passive = passive
        metric.ping = ping
        metric.trace = trace
        metric.secondary = secondary
        measurements.append(metric)
        return measurements
        #for session in self.sessions_list:
            #session dict_keys(['secondary', 'local_diagnosis', 'ping', '_check', 'trace', 'attributes', 'location', 'other'])
        
    def diagnose(self):
        measurements = self.gather_measurements()
