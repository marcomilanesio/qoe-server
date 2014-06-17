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

logger = logging.getLogger('DataManager')

class DataManager():
    def __init__(self, dbconn):
        self.dbconn = dbconn
        #self.dbconn.create_tables()
        
    def _insert_ping_data(self, clientid, clientip, ping_dic):
        sid = int(ping_dic['sid'])
        session_url = ping_dic['session_url'] 
        remoteaddress = str(ping_dic['remoteaddress'])
        ping_min = str(ping_dic['min'])
        ping_max = str(ping_dic['max'])
        ping_avg = str(ping_dic['avg'])
        ping_std = str(ping_dic['std'])
        query = '''insert into %s (clientID, sid, clientIP, session_url, remoteaddress, ping_min, ping_max, ping_avg, ping_std) values (%d, %d, '%s', '%s', '%s', %s, %s, %s, %s)
        ''' % (self.dbconn.get_table_names()['pingtable'], clientid, sid, clientip, session_url, remoteaddress, ping_min, ping_max, ping_avg, ping_std)
        self.dbconn.insert_data_to_db(query)
        logger.info('Inserted ping from probe id [%d] to [%s]' % (clientid, remoteaddress))
        
    '''
    active_data['trace'].append({'sid': sid, 'remoteaddress': remoteaddress, 'step': step_nr, 'step_address': step_addr, 'rtt': step_rtt})
    '''
    def _insert_trace_data(self, clientid, trace_list_of_dic):
        for dic in trace_list_of_dic:
            remoteaddress = dic['remoteaddress'] 
            sid = int(dic['sid'])
            step_nr = int(dic['step'])
            #min_ = dic['min']
            #max_ = dic['max']
            #avg_ = dic['avg']
            #std_ = dic['std']
            '''
            @TODO
            Only one rtt given
            '''
            min_ = max_ = avg_ = std_ = dic['rtt']
            step_addr = dic['step_address']
            if step_addr == '???' or step_addr == 'n.a.':
                step_addr = 'NULL'
                query = '''insert into %s (clientID, sid, remoteaddress, step_nr, step_address, rtt_min, rtt_max, rtt_avg, rtt_std)
                values (%d, %d, '%s', %d, %s, %s, %s, %s, %s)
                ''' % (self.dbconn.get_table_names()['tracetable'], clientid, sid, remoteaddress, step_nr, step_addr, min_, max_, avg_, std_)
            else:
                query = '''insert into %s (clientID, sid, remoteaddress, step_nr, step_address, rtt_min, rtt_max, rtt_avg, rtt_std)
                values (%d, %d, '%s', %d, '%s', %s, %s, %s, %s)
                ''' % (self.dbconn.get_table_names()['tracetable'], clientid, sid, remoteaddress, step_nr, step_addr, min_, max_, avg_, std_)
            self.dbconn.insert_data_to_db(query)
        logger.info('Inserted trace from probe id [%d] to [%s]' % (clientid, remoteaddress))
        
    def insert_data(self, jsondata, client_ip):
        clientid = int(jsondata['clientid'])
        ping = jsondata['ping']
        trace = jsondata['trace'] #list of dic
        self._insert_ping_data(clientid, client_ip, ping)
        self._insert_trace_data(clientid, trace)

    def insert_local_data(self, local_data):
        clientid = int(local_data['clientid'])
        data = local_data['local']
        for k in data.keys():
            dic = data[k]
            page_dim = dic['dim']
            idle_time = dic['idle']
            tot_time = dic['tot']
            http_time = dic['http']
            tcp_time = dic['tcp']
            dns_time = dic['dns']
            cpu_perc = dic['osstats'][0]
            mem_perc = dic['osstats'][1]
            start_time = dic['start']
            query = '''insert into %s (clientID, sid, session_start, t_idle, t_tot, t_http, t_tcp, t_dns, cpu_perc, mem_perc, page_dim) 
            values (%d, %d, '%s', %s, %s, %s, %s, %s, %s, %s, %s)
            ''' % (self.dbconn.get_table_names()['clienttable'], int(clientid), int(k), start_time, idle_time, tot_time, http_time, tcp_time, dns_time, cpu_perc, mem_perc, page_dim )
            self.dbconn.insert_data_to_db(query)
            logger.info('Inserted local stats from probe [%d]' % clientid)
