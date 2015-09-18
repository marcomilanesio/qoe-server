from operator import itemgetter
import numpy

a = [[{'trace_rtt_avg': 0.7709999999999999, 'trace_rtt_min': 0.537, 'trace_hop_nr': 1, 'trace_rtt_std': 0.19881649830937065, 'trace_ip_addr': '192.168.107.3', 'trace_rtt_max': 1.023}, {'trace_rtt_avg': 8.106666666666667, 'trace_rtt_min': 8.097, 'trace_hop_nr': 2, 'trace_rtt_std': 0.007760297817881926, 'trace_ip_addr': '193.55.113.194', 'trace_rtt_max': 8.116}, {'trace_ip_addr': 'n.a.', 'trace_hop_nr': 3},  {'trace_rtt_avg': 9.735666666666667, 'trace_rtt_min': 9.699, 'trace_hop_nr': 4, 'trace_rtt_std': 0.03566822426505484, 'trace_ip_addr': '193.51.177.20', 'trace_rtt_max': 9.784}, {'trace_ip_addr': 'n.a.', 'trace_hop_nr': 5}, {'trace_rtt_avg': 10.762333333333332, 'trace_rtt_min': 10.512, 'trace_hop_nr': 6, 'trace_rtt_std': 0.2282576516911437, 'trace_ip_addr': '72.14.223.254', 'trace_rtt_max': 11.064}, {'trace_rtt_avg': 6.582333333333334, 'trace_rtt_min': 4.739, 'trace_hop_nr': 7, 'trace_endpoints': '209.85.252.194', 'trace_rtt_std': 2.595561510647659, 'trace_ip_addr': '209.85.252.36', 'trace_rtt_max': 10.253}, {'trace_rtt_avg': 16.061333333333334, 'trace_rtt_min': 15.366, 'trace_hop_nr': 8, 'trace_endpoints': '216.239.43.42', 'trace_rtt_std': 0.5108922478261824, 'trace_ip_addr': '216.239.43.68', 'trace_rtt_max': 16.579}, {'trace_rtt_avg': 21.058666666666667, 'trace_rtt_min': 20.928, 'trace_hop_nr': 9, 'trace_endpoints': '216.239.51.110;209.85.248.200', 'trace_rtt_std': 0.09257189398276093, 'trace_ip_addr': '216.239.51.196', 'trace_rtt_max': 21.131}, {'trace_rtt_avg': 20.512333333333334, 'trace_rtt_min': 19.807, 'trace_hop_nr': 10, 'trace_endpoints': '216.239.47.83;216.239.47.87', 'trace_rtt_std': 0.5281984054837312, 'trace_ip_addr': '216.239.51.155', 'trace_rtt_max': 21.078}, {'trace_ip_addr': 'n.a.', 'trace_hop_nr': 11}, {'trace_rtt_avg': 33.297, 'trace_rtt_min': 31.793, 'trace_hop_nr': 12, 'trace_rtt_std': 2.080482636313025, 'trace_ip_addr': '173.194.67.106', 'trace_rtt_max': 36.239}]]


class hop:
    def __init__(self, dic):
        self.ip = dic['trace_ip_addr']
        self.hop_nr = dic['trace_hop_nr']
        try:
            self.rtt_avg = dic['trace_rtt_avg']
        except KeyError:
            self.rtt_avg = None


def analyze_traces(traces):
    r = {}
    for trace in traces:
        for hop in trace:
            if hop['trace_ip_addr'] in r:
                r[hop['trace_ip_addr']]['hop_nr'].append(hop['trace_hop_nr'])
            else:
                r[hop['trace_ip_addr']] = {'rtt': [], 'hop_nr': [hop['trace_hop_nr']]}
            try:
                r[hop['trace_ip_addr']]['rtt'].append(hop['trace_rtt_avg'])
            except KeyError:
                r[hop['trace_ip_addr']]['rtt'].append(None)

    for k, v in r.items():
        if v['rtt'].count(None) == len(v['rtt']):
            continue
        print(k, len(v['hop_nr']), list(set(v['hop_nr'])), numpy.mean(v['rtt']), numpy.std(v['rtt']), "[", numpy.min(v['rtt']), numpy.max(v['rtt']), "]")


def compute_interhop_distance(hops):
    rtts = [hop.rtt_avg for hop in hops]
    ihd = []
    for i in range(len(rtts) - 1):
        try:
            dist = abs(rtts[i+1] - rtts[i])
        except:
            dist = rtts[i+1] if rtts[i+1] is not None else rtts[i]
        ihd.append(dist)

if __name__ == "__main__":
    analyze_traces(a)
