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
import math
import ConfigParser

cusum_conf = './cusum.conf'

class Cusum():
    def __init__(self): 
        self.config = ConfigParser.RawConfigParser()
        self.config.read(cusum_conf)
        self.th = float(self.config.get('cusum','th'))
        self.alpha = float(self.config.get('cusum','alpha'))
        self.c = float(self.config.get('cusum','c'))
    
    def compute(self, list_):
        i = 0
        for sample in list_:
            i += 1
            if (i == 1):
                m = sample
                var = 0.0
                CUSUM = 0.0
                CUSUM_p = CUSUM
            else:
                m_p = self.alpha * m + (1 - self.alpha) * sample   #EWMA
                var_p = self.alpha * var + (1 - self.alpha) * pow((sample - m_p),2)
                L = sample - (m_p + self.c * math.sqrt(var_p))
                CUSUM_p = CUSUM + L
                if (CUSUM_p < 0):
                    CUSUM_p = 0.0
                if (CUSUM_p > self.th):
                    return CUSUM_p
                else:
                    m = m_p
                    var = var_p
                    CUSUM = CUSUM_p
        return None

    def adjust_th(self, th):
        if th > self.th:
            new_th = (1 - self.alpha) * th + self.alpha * self.th
        elif th < self.th:
            new_th = (1 - self.alpha) * self.th + self.alpha * th
        else:
            new_th = self.th

        if new_th != self.th:
            self.config.set('cusum','th', new_th)
            with open(cusum_conf, 'wb') as configfile:
                self.config.write(configfile)
            return new_th
        return -1
