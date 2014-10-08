#!/usr/bin/main
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


class Step():
    def __init__(self, step_nr, step_address, rtt):
        self.step_nr = step_nr
        self.step_address = step_address 
        self.rtt = rtt
    
    def get_step_nr(self):
        return self.step_nr
    
    def get_step_address(self):
        return self.step_address
    
    def get_rtt(self):
        return self.rtt


class Trace():
    def __init__(self, target):
        self.target = target
        self.steps = {}
    
    def get_target(self):
        return self.target

    def get_steps(self):
        return self.steps
    
    def add_step(self, step):
        self.steps[str(step.get_step_nr())] = step
    
    def get_step_number(self, nr):
        if str(nr) in self.steps.keys():
            return self.steps[str(nr)]
        else:
            tmp = map(int, self.steps.keys())
            return self.steps[str(max(tmp))]


class Ping():
    def __init__(self, sid, target, min_, max_, avg, std):
        self.sid = sid
        self.target = target
        self.min_ = min_
        self.max_ = max_
        self.avg_ = avg
        self.std_ = std
    
    def get_sid(self):
        return self.sid
        
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
    def __init__(self, clientid, clientip=''):
        self.clientid = clientid
        self.clientip = clientip
        self.traces = {}
        self.stats = {}
        self.pings = {}
    
    def add_trace(self, sid, trace):
        if str(sid) not in self.traces.keys():
            self.traces[str(sid)] = []
        self.traces[str(sid)].append(trace)
    
    def get_clientid(self):
        return self.clientid
    
    def get_clientip(self):
        return self.clientip
    
    def get_traces(self):
        return self.traces
    
    def get_stats(self):
        return self.stats
    
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
