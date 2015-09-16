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

    def filterout_diagnosed(self, measurements, already_diagnosed):
        filtered = []
        for m in measurements:
            if m.passive.probe_id != self.requesting:
                continue
            for tup in already_diagnosed:
                if m.passive.sid == tup[0] and str(m.passive.session_start) == tup[1]:
                    break
            else:
                filtered.append(m)
        return filtered

    def diagnose(self, url):
        self.extract_data_for_url(url)
        dm = DiagnosisManager(dbname, url, self.requesting)
        measurements = self.gather_measurements()  # all the measurements for a single url
        result = []
        already_diagnosed = dm.get_diagnosed_sessions()
        filtered = self.filterout_diagnosed(measurements, already_diagnosed)
        if not filtered:
            print("no new sessions to diagnose")
            return
        for m in filtered:
            diag = dm.run_diagnosis(m)
            result.append((self.requesting, m.passive.sid, m.passive.session_start, url, diag))
        if result:
            for el in result:
                print(el)
        else:
            print("no new sessions found.")


if __name__ == "__main__":
    r = Reasoner()
    r.diagnose('www.google.com')
