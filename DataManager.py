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
import ConfigParser
import json
from DBConn import DBConn
import logging
import psycopg2
logger = logging.getLogger('DataManager')


class DataManager():
    def __init__(self, probeip, json_data):
        self.db = DBConn()
        self.probeip = probeip
        self.json_data = json_data

        self.sessiontable = self.db.get_table_names()['sessiontable']
        self.summarytable = self.db.get_table_names()['summarytable']
        self.servicestable = self.db.get_table_names()['servicestable']
        self.pingtable = self.db.get_table_names()['pingtable']
        self.tracetable = self.db.get_table_names()['tracetable']
        logger.info("Loaded DB tables.")
        #try:
        #    self._create_table()
        #except psycopg2.ProgrammingError:
        #    logger.warning("Table exists.")
        logger.info("Started for ip [{0}]: storing {1} session(s)".format(self.probeip, len(json_data)))

    def _create_table(self):
        q = '''CREATE TABLE IF NOT EXISTS {0} (id serial NOT NULL,
        probeid INT8 NOT NULL,
        probeip INET,
        sid INT8,
        session_url TEXT,
        session_start TIMESTAMP,
        server_ip INET,
        full_load_time INT,
        page_dim INT,
        cpu_percent INT,
        mem_percent INT,
        services TEXT,
        active_measurements TEXT,
        PRIMARY KEY (id, probeid)
        ) '''.format(self.db.sessiontable)
        self.db.insert_data_to_db(q)

    def insert_data(self):
        stub = '''insert into {0} (probeid, probeip, sid, session_url, session_start, server_ip, full_load_time,
        page_dim, cpu_percent, mem_percent, services, active_measurements) values '''.format(self.db.sessiontable)
        #print len(self.json_data)
        done = []
        for i in range(len(self.json_data)):
            dic = self.json_data[i]
            probeid = dic['probeid']                # 1
            #self.probeip                           # 2
            sid = dic['sid']                        # 3
            session_url = dic['session_url']        # 4
            session_start = dic['session_start']    # 5
            server_ip = dic['server_ip']            # 6
            full_load_time = dic['full_load_time']  # 7
            page_dim = dic['page_dim']              # 8
            cpu_percent = dic['cpu_percent']        # 9
            mem_percent = dic['mem_percent']        # 10
            services = json.dumps(dic['services'])              # 11
            active_measurements = json.dumps(dic['active_measurements'])    # 12

            query = '''{0} ({1},'{2}',{3},'{4}','{5}','{6}',
            {7},{8},{9},{10},'{11}','{12}')'''.format(stub, probeid, self.probeip, sid, session_url, session_start,
                                                      server_ip, full_load_time, page_dim, cpu_percent, mem_percent,
                                                      services, active_measurements)
            try:
                self.db.insert_data_to_db(query)
                done.append(sid)
            except:
                logger.error(query)

        logger.info("Sessions loaded.")
        self.import_data()
        return done

    def import_data(self):
        data = {}
        q = '''select a.probeid, a.probeip, a.sid, a.session_url, a.session_start, a.server_ip, a.full_load_time,
        a.page_dim, a.cpu_percent, a.mem_percent, a.services, a.active_measurements
        from {0} a
        LEFT JOIN {1} b on (a.sid = b.sid and a.probeid = b.probeid and a.session_start = b.session_start)
        where b.sid is NULL;
        '''.format(self.sessiontable, self.summarytable)
        res = self.db.execute_query(q)
        for measure in res:
            data[measure[2]] = {'probeid': measure[0],
                                'probeip': measure[1],
                                'session_url': measure[3],
                                'session_start': measure[4],
                                'server_ip': measure[5],
                                'full_load_time': measure[6],
                                'page_dim': measure[7],
                                'cpu_percent': measure[8],
                                'mem_percent': measure[9],
                                'services': json.loads(measure[10]),
                                'active_measurements': json.loads(measure[11])}

        logger.info("Fetched {0} new sessions from the db".format(len(data)))

        for sid, session in data.iteritems():
            q = '''insert into {0} (probeid, probeip, sid, session_url, session_start, server_ip, full_load_time,
            page_dim, cpu_percent,mem_percent ) values
            ({1}, '{2}', {3}, '{4}', '{5}', '{6}', {7}, {8}, {9}, {10})'''.format(self.summarytable, session['probeid'],
                                                                                  session['probeip'], sid,
                                                                                  session['session_url'],
                                                                                  session['session_start'],
                                                                                  session['server_ip'],
                                                                                  session['full_load_time'],
                                                                                  session['page_dim'],
                                                                                  session['cpu_percent'],
                                                                                  session['mem_percent'])
            self.db.insert_data_to_db(q)

            for service in session['services']:
                q1 = '''insert into {0} (probeid, sid, session_url, session_start, service_base_url, service_ip,
                netw_bytes, t_tcp, t_http, rcv_time, nr_obj) values ({1}, {2}, '{3}', '{4}', '{5}', '{6}', {7}, {8},
                {9}, {10}, {11})'''.format(self.servicestable, session['probeid'], sid, session['session_url'],
                                           session['session_start'], service['base_url'], service['ip'],
                                           service['netw_bytes'], service['sum_syn'], service['sum_http'],
                                           service['sum_rcv_time'], service['nr_obj'])

                self.db.insert_data_to_db(q1)

            for ip, active_measure in session['active_measurements'].iteritems():
                trace = None
                ping = json.loads(active_measure['ping'])
                if 'trace' in active_measure.keys() and active_measure['trace'] is not None:
                    trace = json.loads(active_measure['trace'])
                if len(ping) == 0:
                    logger.error("Loaded 0 len ping dictionary, skipping")
                    continue

                try:
                    q2 = '''insert into {0} (probeid, sid, session_start, server_ip, host, min, max, avg, std, loss) values
                    ({1}, {2}, '{3}', '{4}', '{5}', {6}, {7}, {8}, {9}, {10})'''.format(self.pingtable, session['probeid'],
                                                                                        sid, session['session_start'],
                                                                                        session['server_ip'], ping['host'],
                                                                                        ping['min'], ping['max'],
                                                                                        ping['avg'], ping['std'],
                                                                                        ping['loss'])
                    self.db.insert_data_to_db(q2)
                except KeyError as e:
                    print e
                    exit(-1)

                if not trace:
                    logger.debug("Trace not present [either hop or service], skipping")
                    continue

                if len(trace) == 0:
                    logger.error("Loaded 0 len trace list, skipping")
                    continue

                for step in trace:
                    rtt = step['rtt']
                    if rtt == -1:
                        q3 = '''insert into {0} (probeid, sid, session_start, server_ip, hop_nr, min, max, avg,
                        std, endpoints) values ({1}, {2}, '{3}', '{4}', {5}, {6}, {7},
                        {8}, {9}, '{10}')'''.format(self.tracetable, session['probeid'], sid, session['session_start'],
                                                    session['server_ip'], step['hop_nr'], -1, -1, -1, -1,
                                                    json.dumps(step['endpoints']))
                    else:
                        q3 = '''insert into {0} (probeid, sid, session_start, server_ip, hop_addr, hop_nr, min, max,
                        avg, std, endpoints) values ({1}, {2}, '{3}', '{4}', '{5}', {6}, {7}, {8}, {9}, {10}, '{11}')
                        '''.format(self.tracetable, session['probeid'], sid, session['session_start'],
                                   session['server_ip'], step['ip_addr'], step['hop_nr'], rtt['min'], rtt['max'],
                                   rtt['avg'], rtt['std'], json.dumps(step['endpoints']))

                    self.db.insert_data_to_db(q3)

        logger.info("Session(s) successfully imported.")