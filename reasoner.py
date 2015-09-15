from collections import namedtuple
from diagnosis import DiagnosisManager
from extract import Extractor

dbname = 'reasoner.db'


class Reasoner:
    
    def __init__(self, probe_id=1190855395):
        self.sessions_list = []
        self.requesting = probe_id

    def extract_data_for_url(self, url):
        e = Extractor(url)
        self.sessions_list = e.extract()

    @staticmethod
    def _process_passive(dic):
        passive = namedtuple('passive', ['probe_id', 'sid', 'server_ip', 'session_start', 'full_load_time', 'page_dim',
                                         'mem_percent', 'cpu_percent'])
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
        for session in self.sessions_list:
            # ['secondary', 'local_diagnosis', 'ping', '_check', 'trace', 'attributes', 'location', 'other']
            metric = namedtuple('metrics', ['passive', 'ping', 'trace', 'secondary'])
            metric.passive = Reasoner._process_passive(session.other)
            metric.secondary = session.secondary
            metric.ping = session.ping
            metric.trace = session.trace
            measurements.append(metric)
        return measurements

    def diagnose(self, url):
        self.extract_data_for_url(url)
        dm = DiagnosisManager(dbname, url, self.requesting)
        measurements = self.gather_measurements()  # all the measurements for a single url
        other_probes = []
        for m in measurements:
            if not m.passive.probe_id == self.requesting:
                other_probes.append(m)
                continue
            diag = dm.run_diagnosis(m)
            print(diag)






if __name__ == "__main__":
    r = Reasoner()
    r.diagnose('www.google.com')
