#!/usr/bin/main

class Step():
    def __init__(self, sid, step_nr, step_address, rtt):
        self.sid = sid
        self.step_nr = step_nr
        self.step_address = step_address 
        self.rtt = rtt
    
    def get_step_nr(self):
        return self.step_nr
    
    def get_step_address(self):
        return self.step_address
    
    def get_rtt_step(self):
        return self.rtt

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
    

class Probe():
    def __init__(self, clientid, clientip):
        self.clientid = clientid
        self.clientip = clientip
        self.traces = []
    
    def get.clientid(self):
        return self.clientid
    
    def get.clientip(self):
        return self.clientip
    
    def get_traces(self):
        return self.traces
    
    def add_trace(self, trace):
        self.traces.append(trace)
    
