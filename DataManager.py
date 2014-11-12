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
        try:
            self._create_table()
        except psycopg2.ProgrammingError:
            logger.warning("Table exists.")
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

            self.db.insert_data_to_db(query)
            return True
