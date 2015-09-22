#!/usr/bin/python3

import socketserver
import urllib.request
import json

from webqoe.reasoner import Reasoner


def check_url(url):
    try:
        urllib.request.urlopen(url)
    except:
        try:
            urllib.request.urlopen('http://' + url)
        except:
            return False
    return True


class MyTCPHandler(socketserver.BaseRequestHandler):
    """
    The RequestHandler class for our server.

    It is instantiated once per connection to the server, and must
    override the handle() method to implement communication to the
    client.
    """

    def handle(self):
        # self.request is the TCP socket connected to the client
        data = self.request.recv(1024).decode().strip()
        try:
            jsondata = json.loads(data)
            print('received:', jsondata)
            probe = jsondata['probe']
            url = jsondata['url']
            globaldiag = jsondata['global']
        except:
            answer = "Unable to parse response"
            self.request.sendall(answer.encode())
            return

        print("{0} asked for [{1} : {2}]:".format(self.client_address[0], jsondata['probe'], jsondata['url']))
        if not check_url(url):
            answer = "URL not valid\n"
            self.request.sendall(answer.encode())
            return

        r = Reasoner()
        res = r.diagnose(probe, url, globaldiag)
        answer = "{}\n".format(json.dumps(res))
        self.request.sendall(answer.encode())
        print("sent.")

if __name__ == "__main__":
    HOST, PORT = "", 50007
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    server = socketserver.ThreadingTCPServer((HOST, PORT), MyTCPHandler)
    #CTRL-C to kill
    server.serve_forever()
