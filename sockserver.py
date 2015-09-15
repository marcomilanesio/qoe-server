#!/usr/bin/python3

import socketserver
import urllib.request
from extract import Extractor
from reasoner import Reasoner

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
        self.data = self.request.recv(1024).decode().strip()
        print("{0} asked for {1}:".format(self.client_address[0], self.data))
        if not check_url(self.data):
            answer = "No results found\n"
            self.request.sendall(answer.encode())
            return
    
        e = Extractor(self.data)
        res = e.extract(None)
        e.close()
        r = Reasoner(res, self.data)
        r.diagnose()
        # just send back the same data, but upper-cased
        answer = "Found {} results\n".format(len(res))
        self.request.sendall(answer.encode())

if __name__ == "__main__":
    HOST, PORT = "", 50007
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    server = socketserver.ThreadingTCPServer((HOST, PORT), MyTCPHandler)
    #CTRL-C to kill
    server.serve_forever()
