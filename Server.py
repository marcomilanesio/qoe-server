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
import ConfigParser
import re
from DataManager import DataManager
from DBConn import DBConn
import logging
import logging.config
import Utils
from DiagnosisServer import DiagnosisServer

CONF_FILE = './server.conf'


class JSONServer(SocketServer.ThreadingTCPServer):
    allow_reuse_address = True


class JSONServerHandler(SocketServer.StreamRequestHandler):
    def handle(self):
        dbconn = DBConn()
        clientip = self.client_address[0]
        try:
            data = self.rfile.readline().strip()
            msg = "received {0} bytes from {1}".format(len(data), clientip)
            logger.info(msg)
            answer = {'Server says': msg, 'sids': []}
            if re.match("check: ", data):
                pass
            else:
                json_data = json.loads(data)
                logger.info("Got data for %d sessions" % len(json_data))
                tmp = []
                for session in json_data:
                    tmp.append(session['sid'])
                    logger.info("Received sessions {0}".format(tmp))
                answer['sids'] = tmp
                self.request.sendall(json.dumps(answer))
                datamanager_srv = DataManager(dbconn)
                for session in json_data:
                    # ['passive', 'active', 'ts', 'clientid', 'sid']
                    logger.info("Saving data for session {0} from probe {1}...".format(session['sid'],
                                                                                       session['clientid']))
                    datamanager_srv.insert_local_data(session['sid'], session['clientid'], session['passive'])
                    for i in range(len(session['active'])):
                        #{u'ping':{}, u'clientid':int, u'trace':{}}
                        current = session['active'][i]
                        datamanager_srv.insert_data(current, clientip)
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
