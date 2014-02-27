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
import psycopg2
import sys
import ConfigParser

conf_file = './server.conf'

class DBConn():
    def __init__(self):
        self.config = ConfigParser.RawConfigParser()
        self.config.read(conf_file)
        self.dbname = self.config.get('server', 'dbname')
        self.dbuser = self.config.get('server', 'dbuser')
        self.pingtable = self.config.get('server', 'pingtable')
        self.tracetable = self.config.get('server', 'tracetable')
        self.clienttable = self.config.get('server', 'clienttable')
        self.diagnosistable = self.config.get('server', 'diagnosistable')
        self.tables = [self.pingtable, self.tracetable, self.clienttable, self.diagnosistable]
        try:
            self.conn = psycopg2.connect(database=self.dbname, user=self.dbuser) 
        except psycopg2.DatabaseError, e:
            print 'Unable to connect to DB. Error %s' % e
            sys.exit(1)

    def get_table_names(self):
        return {'pingtable': self.pingtable, 'tracetable': self.tracetable, 'clienttable': self.clienttable, 'diagnosistable': self.diagnosistable}
        
    def insert_data_to_db(self, q):
        cursor = self.conn.cursor()
        cursor.execute(q)
        self.conn.commit()

    def execute_query(self, q):
        cur = self.conn.cursor()
        cur.execute(q)
        res = cur.fetchall()
        return res
    
    def get_config(self):
        return self.config
