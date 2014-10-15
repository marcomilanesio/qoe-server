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
import SocketServer
import json
import psycopg2
import ConfigParser
import re
import Utils
from DataManager import DataManager
from DiagnosisServer import DiagnosisServer
from DBConn import DBConn
import logging
import logging.config
from contextlib import closing

CONF_FILE = './server.conf'


class JSONServer(SocketServer.ThreadingTCPServer):
    allow_reuse_address = True


class JSONServerHandler(SocketServer.StreamRequestHandler):
    def handle(self):
        #dbconn = DBConn()
        clientip = self.client_address[0]
        try:
            data = self.rfile.readline().strip()
            msg = "received {0} bytes from {1}".format(len(data), clientip)
            logger.info(msg)
            answer = {'Server says': msg}
            self.request.sendall(json.dumps(answer))
            if re.match("check: ", data):
                pass
            else:
                json_data = json.loads(data)
                logger.info("Got data for %d sessions" % len(json_data))
                #datamanager_srv = DataManager(dbconn)
                for session in json_data:
                    # ['passive', 'active', 'ts', 'clientid', 'sid']
                    logger.info("Saving data for session {0} from probe {1}...".format(session['sid'],
                                                                                       session['clientid']))
                    #datamanager_srv.insert_local_data(session['sid'], session['clientid'], session['passive'])
                    for i in range(len(session['active'])):
                        #[u'ping', u'clientid', u'trace']
                        print session['active'][i].keys()


            '''
            data = self.rfile.readline().strip()
            logger.info('received data from %s ' % clientip)
            if re.match('check: ', data):
                result = {}
                received = json.loads(data[7:])
                url_to_diagnose = received['url']
                clientid = int(received['clientid'])
                logger.debug('check message for %s from %d' % ( url_to_diagnose, clientid))
                time_range = received['time_range']
                #print 'time_range:' , time_range
                try:
                    if Utils.check_url(url_to_diagnose):
                        logger.debug('URL validated')
                        ds = DiagnosisServer(dbconn, clientid, clientip, url_to_diagnose)
                        res = ds.get_result(time_range)
                        result = {'return': json.dumps(res)}
                    else:
                        result = {'return': '[utils] url malformed'}
                except ValueError:
                    logger.warning('url malformed')
                    result = {'return': 'url malformed'}
                self.request.sendall(json.dumps(result))
            else:
                datamanager_srv = DataManager(dbconn)
                if re.match('local: ', data):
                    logger.debug('local stats received')
                    local_data = json.loads(data[7:])
                    datamanager_srv.insert_local_data(local_data)
                else:
                    logger.debug('ping/trace data received')
                    jsondata = json.loads(data)
                    datamanager_srv.insert_data(jsondata, clientip)
                self.request.sendall(json.dumps({'return': 'data inserted'}))
            '''
        except Exception, e:
            logger.error('Exception while receiving message: %s' % e)
            pass


logging.config.fileConfig('logging.conf')
logger = logging.getLogger('server')
config = ConfigParser.RawConfigParser()
config.read(CONF_FILE)
ip_ = config.get('server', 'ip')
port_ = int(config.get('server', 'port'))
server = JSONServer((ip_, port_), JSONServerHandler)
logger.info('Server started on %s:%d' % (ip_, port_))
server.serve_forever()
