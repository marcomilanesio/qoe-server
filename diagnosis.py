#!/usr/bin/python

import logging
import json
from cusum import Cusum
from collections import OrderedDict
import sqlite3
import re
import os

DBNAME = 'reasoner.db'
PASSIVE_TH_TABLE = 'passive_threshold'
CUSUM_TH_TABLE = 'cusum_threshold'
RESULT_TABLE = 'diagnosis'

logging.basicConfig(filename='diagnosis.log', format='%(asctime)s - %(levelname)s: %(message)s', level=logging.DEBUG)


class DB:
    def __init__(self, dbname):
        if not os.path.isfile(dbname):
            self.conn = sqlite3.connect(dbname)
            self.create_tables()
        else:
            self.conn = sqlite3.connect(dbname)

    def create_tables(self):
        q = '''create table if not exists {0} (url TEXT, probe_id INT, flt INT, http INT, tcp INT, dim INT, cnt INT,
            unique(url,probe_id))'''.format(PASSIVE_TH_TABLE)
        self.execute_query(q)
        q = '''CREATE TABLE IF NOT EXISTS {0} (name TEXT, url TEXT, probe_id INT, cusumT1 TEXT, cusumD1 TEXT,
              cusumD2 TEXT, cusumDH TEXT, unique(name,url,probe_id) )'''.format(CUSUM_TH_TABLE)
        self.execute_query(q)
        q = '''CREATE TABLE IF NOT EXISTS {0} (sid INT, url TEXT, when_browsed datetime, probe_id INT, diagnosis TEXT,
              unique(url, when_browsed, probe_id))'''.format(RESULT_TABLE)
        self.execute_query(q)

    def execute_query(self, query, tup=None):
        create = re.compile('create', re.IGNORECASE)
        select = re.compile('select', re.IGNORECASE)
        insert = re.compile('insert', re.IGNORECASE)
        update = re.compile('update', re.IGNORECASE)
        c = self.conn.cursor()
        if not tup:
            c.execute(query)
            if re.match(create, query) or re.match(update, query):
                self.conn.commit()
                return
            elif re.match(select, query):
                result = c.fetchall()
                return result
            elif re.match(insert, query):
                self.conn.commit()
                return c.lastrowid
            else:
                logging.error("Query not supported. {0}".format(query))
                self.conn.commit()
        else:  # parameters in insert as tuple
            c.execute(query, tup)
            self.conn.commit()
            return c.lastrowid


class DiagnosisManager:
    def __init__(self, dbname, url, probe_id):
        self.url = url
        self.db = DB(dbname)
        self.requesting = probe_id
        self.passive_thresholds = self.get_passive_thresholds()
        if self.passive_thresholds:
           self.cusums = self.get_cusums()
        else:
            self.cusums = {}
        logging.info("Diagnosis Manager started ({0}) for {1}".format(self.url, self.requesting))

    def get_passive_thresholds(self):
        q = '''select flt, http, tcp, dim, cnt from {0} where url like '%{1}%' and probe_id = {2} '''\
            .format(PASSIVE_TH_TABLE, self.url, self.requesting)
        try:
            res = self.db.execute_query(q)
            data = res[0]
            return {'full_load_time_th': data[0], 'http_th': data[1], 'tcp_th': data[2],
                    'dim_th': data[3], 'count': data[4]}
        except IndexError:
            logging.debug("Never browsed {0}-{1}".format(self.url, self.requesting))
            return None

    def get_cusums(self):
        cusums = {}
        names = ['cusumT1', 'cusumD1', 'cusumD2', 'cusumDH']
        q = '''select {0} from {1} where url like '%{2}%' and probe_id = {3}'''.format(','.join(names), CUSUM_TH_TABLE,
                                                                                       self.url, self.requesting)
        res = self.db.execute_query(q)
        if len(res) == 0:
            logging.info("No cusums available for {0} - {1}: creating new ones.".format(self.url, self.requesting))
            return dict.fromkeys(names)
        if len(res) > 1:
            logging.warning("Got multiple values for url {0} - {1}".format(self.url, self.requesting))
        row = res[0]
        for idx, el in enumerate(row):
            dic = json.loads(el)
            cusums[names[idx]] = Cusum(name=dic['name'], th=dic['th'], value=dic['cusum'], mean=dic['mean'],
                                       var=dic['var'], count=dic['count'])
        return cusums

    def insert_first_locals(self, flt, http, tcp, dim):
        q = "insert into {0}(url, probe_id, flt, http, tcp, dim, cnt) values "\
            .format(PASSIVE_TH_TABLE)
        q += "('{0}', {1}, {2}, {3}, {4}, {5}, 1)".format(self.url, self.requesting, flt, http, tcp, dim)
        self.db.execute_query(q)

    def update_cusums(self, first=False):
        keys = list(self.cusums.keys())
        d = dict.fromkeys(keys, None)
        for k in keys:
            d[k] = self.cusums[k].__dict__
        if first:
            q = '''insert into {0} (url, probe_id, {1}) values ('{2}', {3},'''.format(CUSUM_TH_TABLE, ','.join(keys),
                                                                                      self.url, self.requesting)
            q += ','.join("'" + json.dumps(d[k]) + "'" for k in keys) + ')'
            self.db.execute_query(q)
        else:
            for k, v in self.cusums.items():
                q = '''update {0} set {1} = {2} where url = '{3}' and probe_id = {4}'''\
                    .format(CUSUM_TH_TABLE, k, "'" + json.dumps(d[k]) + "'", self.url, self.requesting)
                self.db.execute_query(q)
        #logging.info("Cusum table updated.")

    def prepare_for_diagnosis(self, measurement):
        TRAINING = 100
        if not measurement.passive.sid:
            logging.error("sid not specified. Unable to run diagnosis: {0} - {1}.".format(self.url, self.requesting))
            return

        locals_th = self.get_passive_thresholds()
        if any([self.cusums[i] for i in self.cusums]):
            logging.info("Cusums loaded for {0} - {1}".format(self.url, self.requesting))
        # get current data for cusum update

        #trace = [x['trace'] for x in active if x['trace'] is not None][0]
        trace = measurement.trace
        h1 = [x for x in trace if x['trace_hop_nr'] == 1][0]['trace_rtt_max']
        addr1 = [x for x in trace if x['trace_hop_nr'] == 1][0]['trace_ip_addr']
        h2 = [x for x in trace if x['trace_hop_nr'] == 2][0]['trace_rtt_max']
        addr2 = [x for x in trace if x['trace_hop_nr'] == 2][0]['trace_ip_addr']
        try:
            h3 = [x for x in trace if x['trace_hop_nr'] == 3][0]['trace_rtt_max']
            addr3 = [x for x in trace if x['trace_hop_nr'] == 3][0]['trace_ip_addr']
        except KeyError:  # FIXME quick & dirty
            h3 = h2 + 0.1
            addr3 = 'n.a.'

        http_time = sum([x['secondary_sum_http'] for x in measurement.secondary])
        tcp_time = sum([x['secondary_sum_syn'] for x in measurement.secondary])

        if not locals_th:
            logging.info("First time hitting {0} for {1}: using current values.".format(self.url, self.requesting))
            time_th = measurement.passive.full_load_time + 1000
            http_th = http_time + 50
            tcp_th = tcp_time + 50
            dim_th = measurement.passive.page_dim + 5000
            #rcv_th = sum([x['sum_rcv_time'] for x in browser]) + 50  # TODO add rcv_th to local_diag
            self.insert_first_locals(time_th, http_th, tcp_th, dim_th)
        else:
            time_th = locals_th['full_load_time_th']
            dim_th = locals_th['dim_th']
            http_th = locals_th['http_th']
            tcp_th = locals_th['tcp_th']

         # TODO: find a way to have threshold setting
        th_t1 = h1 + 0.1
        d1 = h2 - h1
        th_d1 = d1 + 0.2
        d2 = h3 - h2
        th_d2 = d2 + 0.3
        dh = http_time - tcp_time
        th_dh = dh + 0.5

        active_subset = {'hop1': {'ip': addr1, 'rtt': h1},
                         'hop2': {'ip': addr2, 'rtt': h2},
                         'hop3': {'ip': addr3, 'rtt': h3},
                         'http_time': http_time,
                         'tcp_time': tcp_time,
                         'th_t1': th_t1,
                         'th_d1': th_d1,
                         'th_d2': th_d2,
                         'th_dh': th_dh
                         }

        if not any([self.cusums[i] for i in self.cusums]):
            self.cusums['cusumT1'] = Cusum(name='cusumT1', th=h1, value=h1)
            self.cusums['cusumD1'] = Cusum(name='cusumD1', th=d1, value=d1)
            self.cusums['cusumD2'] = Cusum(name='cusumD2', th=d2, value=d2)
            self.cusums['cusumDH'] = Cusum(name='cusumDH', th=dh, value=dh)
            self.update_cusums(first=True)
        else:
            if self.cusums['cusumT1'].get_count() < TRAINING:
                self.cusums['cusumT1'].compute(h1)
            if self.cusums['cusumD1'].get_count() < TRAINING:
                self.cusums['cusumD1'].compute(d1)
            if self.cusums['cusumD2'].get_count() < TRAINING:
                self.cusums['cusumD2'].compute(d2)
            if self.cusums['cusumDH'].get_count() < TRAINING:
                self.cusums['cusumDH'].compute(http_time - tcp_time)
            self.update_cusums()

        mem_th = cpu_th = 50

        passive_thresholds = {'time_th': time_th,
                              'dim_th': dim_th,
                              'http_th': http_th,
                              'tcp_th': tcp_th,
                              'mem_th': mem_th,
                              'cpu_th': cpu_th}

        return active_subset, passive_thresholds

    def run_diagnosis(self, measurement):
        diagnosis = OrderedDict({'result': None, 'details': None})
        active_subset, passive_thresholds = self.prepare_for_diagnosis(measurement)
        http_time = active_subset['http_time']
        tcp_time = active_subset['tcp_time']
        if not (measurement.passive and measurement.trace and measurement.ping
                and measurement.secondary and passive_thresholds):
            diagnosis['result'] = 'Error'
            diagnosis['details'] = 'Unable to retrieve data'
            return diagnosis

        if measurement.passive.full_load_time < passive_thresholds['time_th']:
            diagnosis['result'] = 'No problem found.'
            diagnosis['details'] = ''
        else:
            if measurement.passive.mem_percent > passive_thresholds['mem_th'] or \
                            measurement.passive.cpu_percent > passive_thresholds['cpu_th']:
                diagnosis['result'] = 'Client overloaded'
                diagnosis['details'] = "mem = {0}%, cpu = {1}%".format(measurement.passive.mem_percent,
                                                                       measurement.passive.cpu_percent)
                return diagnosis

            if http_time < passive_thresholds['http_th']:
                if measurement.passive.page_dim > passive_thresholds['dim_th']:
                    diagnosis['result'] = 'Page too big'
                    diagnosis['details'] = "page_dim = {0} bytes".format(measurement.passive.page_dim)
                elif tcp_time > passive_thresholds['tcp_th']:
                    diagnosis['result'] = 'Web server too far'
                    diagnosis['details'] = "sum_syn = {0} ms".format(tcp_time)
                else:
                    diagnosis['result'] = 'No problem found'
                    diagnosis['details'] = "Unable to get more details"
            else:
                diagnosis['result'], diagnosis['details'] = self._check_network(active_subset)

        q = "update {0} set cnt = cnt + 1 where url like '%{1}%' and probe_id = {2}"\
            .format(PASSIVE_TH_TABLE, self.url, self.requesting)

        self.db.execute_query(q)
        self.store_diagnosis_result(measurement, diagnosis)
        logging.info("Diagnosis result stored {0} - {1}".format(self.url, self.requesting))
        return diagnosis

    def _check_network(self, active_subset):
        result = details = None
        gw_addr, gw_rtt = active_subset['hop1']['ip'], active_subset['hop1']['rtt']
        second_addr, second_rtt = active_subset['hop2']['ip'], active_subset['hop2']['rtt']
        third_addr, third_rtt = active_subset['hop3']['ip'], active_subset['hop3']['rtt']

        if self.cusums['cusumT1'].compute(gw_rtt):
            result = 'Local congestion (LAN/GW)'
            details = "cusum on RTT to 1st hop {0}".format(gw_addr)
        else:
            d1 = second_rtt - gw_rtt
            d2 = third_rtt - second_rtt
            if self.cusums['cusumD1'].compute(d1):
                if self.cusums['cusumD2'].compute(d2):
                    result = 'Network congestion'
                    details = "cusum on Delta1 [{0},{1}] and Delta2 [{1},{2}]".format(gw_addr, second_addr, third_addr)
                else:
                    result = 'Gateway congestion'
                    details = "cusum on Delta1 [{0},{1}]".format(gw_addr, second_addr)

        if not result:
            diff = active_subset['http_time'] - active_subset['tcp_time']
            if self.cusums['cusumDH'].compute(diff):
                result = 'Remote Web Server'
                details = "cusum on t_http - t_tcp"
            else:
                result = 'Network generic (far)'
                details = "Unable to get more details"

        return result, details

    def store_diagnosis_result(self, measurement, diagnosis):
        sid = measurement.passive.sid
        when = measurement.passive.session_start
        q = "insert into {0} (sid, url, when_browsed, probe_id, diagnosis) values".format(RESULT_TABLE)
        q += " ({0}, '{1}', '{2}', {3}, '{4}')".format(sid, self.url, when, self.requesting, json.dumps(diagnosis))
        self.db.execute_query(q)

