__author__ = 'marco'

import ConfigParser
import re
from DBConn import DBConn
import math


cusum_conf = './cusum.conf'


class Cusum():
    def __init__(self, cusum_name):
        self.config = ConfigParser.RawConfigParser()
        self.config.read(cusum_conf)
        self.th = float(self.config.get(cusum_name, 'th'))
        self.alpha = float(self.config.get('cusum', 'alpha'))
        self.c = float(self.config.get('cusum', 'c'))

        self.m = 0.0
        self.var = 0.0
        self.CUSUM = 0.0
        self.CUSUMm = 0.0
        self.CUSUMvar = 0.0

    def compute(self, list_):
        i = 0
        for sample in list_:
            i += 1
            if i == 1:
                self.m = sample
                self.CUSUM = sample
                self.CUSUMm = sample
            else:
                self.m = self.alpha * self.m + (1 - self.alpha) * sample   #EWMA
                self.var = self.alpha * self.var + (1 - self.alpha) * pow((sample - self.m), 2)
                L = sample - (self.m + self.c * math.sqrt(self.var))  # incremento CUSUM
                self.CUSUM += L
                if self.CUSUM < 0:
                    self.CUSUM = 0.0
                self.CUSUMm = self.alpha * self.CUSUMm + (1 - self.alpha) * self.CUSUM  # EWMA
                self.CUSUMvar = self.alpha * self.CUSUMvar + (1 - self.alpha) * pow((self.CUSUM - self.CUSUMm), 2)

    def adjust_threshold(self):
        new_th = 0 * self.CUSUMm + 3 * self.CUSUMvar
        return new_th


class ThresholdTrainer():
    def __init__(self, clientid, num_training_session):
        self.configCusum = ConfigParser.RawConfigParser()
        self.configCusum.read(cusum_conf)
        self.N = num_training_session
        self.cusum_objects = {}
        self.alpha = float(self.configCusum.get('cusum', 'alpha'))
        self.c = float(self.configCusum.get('cusum', 'c'))
        self.dbconn = DBConn()
        self.clientid = clientid

    def add_cusum(self):
        for cusum_name in self.configCusum.sections():
            if re.search('[A-Z]', cusum_name):
                self.cusum_objects[cusum_name] = Cusum(cusum_name)

    def get_data_for_training(self, cusum_name):
        if cusum_name == 'cusumT1':
            step_nr = 1
        elif cusum_name == 'cusumT2T1':
            step_nr = 2
        elif cusum_name == 'cusumT3T2':
            step_nr = 3
        else:
            step_nr = None
        if step_nr:
            query = '''select sid, max(avg) from %s where hop_nr = %d and
                probeid = %d group by sid order by sid asc limit %d;''' % (self.dbconn.get_table_names()['tracetable'],
                                                                  step_nr, self.clientid, self.N)
        if cusum_name == 'cusumTHTTPTTCP':
            query = '''select sid, (sum(t_http) - sum(t_tcp)) as diff from %s where probeid = %d group by sid
            order by sid asc limit %d''' % (self.dbconn.get_table_names()['servicestable'], self.clientid, self.N)

        if query:
            res = self.dbconn.execute_query(query)
            return res

if __name__ == '__main__':
    clientid = 6757187
    num_training_sessions = 100
    t = ThresholdTrainer(clientid, num_training_sessions)
    t.add_cusum()
    res = {}

    step1 = [float(x[1]) for x in t.get_data_for_training('cusumT1')]
    step2 = [float(x[1]) for x in t.get_data_for_training('cusumT2T1')]
    step3 = [float(x[1]) for x in t.get_data_for_training('cusumT3T2')]
    step4 = [float(x[1]) for x in t.get_data_for_training('cusumTHTTPTTCP')]

    t1hop = step1
    t2hop = [x-y for x, y in zip(step2, step1)]
    t3hop = [x-y for x, y in zip(step3, step2)]

    res['cusumT1'] = t1hop
    res['cusumT2T1'] = t2hop
    res['cusumT3T2'] = t3hop
    res['cusumTHTTPTTCP'] = step4

    i = 0
    while i < num_training_sessions - 1:
        i += 1
        for k, cusum in t.cusum_objects.iteritems():
            c = t.cusum_objects[k]
            data = res[k][:i]
            c.compute(data)
    else:
        for k, cusum in t.cusum_objects.iteritems():
            c = t.cusum_objects[k]
            new_th = c.adjust_threshold()
            t.configCusum.set(k, 'th', new_th)
            print("{0} \t - {1}".format(k, new_th))


    with open(cusum_conf, 'wb') as configfile:
        t.configCusum.write(configfile)
