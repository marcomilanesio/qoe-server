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
        clientip = self.client_address[0]
        data = None
        try:
            data = self.rfile.readline().strip()
            msg = "received {0} bytes from {1}".format(len(data), clientip)
            logger.info(msg)
            answer = {'Server says': msg, 'sids': []}
        except Exception, e:
            logger.error('Exception while receiving message: %s' % e)
            pass

        if data:
            if re.match("check: ", data):
                pass
            else:
                json_data = json.loads(data)  # list of dictionary
                logger.info("Got data for %d session(s)" % len(json_data))
                tmp = []
                for session in json_data:
                    tmp.append(session['sid'])
                logger.info("Received session(s) {0}".format(tmp))
                answer['sids'] = tmp
                self.request.sendall(json.dumps(answer))
                datamanager_srv = DataManager(clientip, json_data)
                if datamanager_srv.insert_data():
                    logger.info("Data inserted.")
        else:
            answer = {'Server says': 'Unable to load json data.'}
            self.request.sendall(json.dumps(answer))


logging.config.fileConfig('logging.conf')
logger = logging.getLogger('server')
config = ConfigParser.RawConfigParser()
config.read(CONF_FILE)
ip_ = config.get('server', 'ip')
port_ = int(config.get('server', 'port'))
server = JSONServer((ip_, port_), JSONServerHandler)
logger.info('Server started on %s:%d' % (ip_, port_))
server.serve_forever()
