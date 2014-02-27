#!/usr/bin/main

class Step():
    def __init__(self, step_nr, step_address, rtt):
        self.step_nr = step_nr
        self.step_address = step_address 
        self.rtt = rtt
    
    def get_step_nr(self):
        return self.step_nr
    
    def get_step_address(self):
        return self.step_address
    
    def get_rtt_step(self):
        return self.rtt
    
    def __str__(self):
        s = '%d - %s - %f' % (self.step_nr, self.step_address, self.rtt)
        return s

class Trace():
    def __init__(self, probe, target, sid):
        self.probe = probe
        self.target = target
        self.sid = sid
        self.steps = []
    
    def get_probe(self):
        return self.probe
        
    def get_sid(self):
        return self.sid
    
    def get_target(self):
        return self.target

    def get_steps(self):
        return self.steps
    
    def add_step(self, step):
        self.step.append(step)
    
class Ping():
    def __init__(self, target, min_, max_, avg, std):
        self.target = target
        self.min_ = min_
        self.max_ = max_
        self.avg_ = avg
        self.std_ = std
    
    def get_min(self):
        return self.min_
    
    def get_max(self):
        return self.max_
        
    def get_avg(self):
        return self.avg_
    
    def get_std(self):
        return self.std_

    def get_target(self):
        return self.target
        
        
class Probe():
    def __init__(self, clientid, clientip='', url=''):
        self.clientid = clientid
        self.clientip = clientip
        self.traces = {}
        self.stats = {}
        self.url = url
        self.pings = {}
    
    def get_clientid(self):
        return self.clientid
    
    def get_clientip(self):
        return self.clientip
    
    def get_traces(self):
        return self.traces
    
    def get_stats(self):
        return self.stats
    
    def get_url(self):
        return self.url
    
    def add_trace(self, sid, trace):
        if str(sid) not in self.traces.keys():
            self.traces[str(sid)] = []
        self.traces[str(sid)].append(trace)
    
    def set_trace(self, traces):
        self.traces = traces
        
    def add_stat_value(self, sid, key, value):
        if str(sid) not in self.stats.keys():
            self.stats[str(sid)] = {}
        self.stats[str(sid)][key] = value
        
    def add_ping(self, sid, ping):
        if str(sid) not in self.pings.keys():
            self.pings[str(sid)] = []
        self.pings[str(sid)].append(ping)
    
    def get_sids(self):
        res = [int(x) for x in self.stats.keys()]
        return res
        
    def __str__(self):
        return str(self.pings)
        #return str(self.traces)
        #return str(self.stats)
    
