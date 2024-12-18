from tntserver.Nodes.Node import *
import sys
import os
from os.path import dirname
from tntserver.globals import root_path

from threading import Thread
from http.server import SimpleHTTPRequestHandler
import threading
import time

class HttpServer(Thread):
    filepath = None

    def __init__(self, path, port):
        threading.Thread.__init__(self)
        HttpServer.filepath = path
        self.port = port

    def run(self):
        import http.server
        import socketserver
        handler = CORSRequestHandler
        while True:
            try:
                d = socketserver.TCPServer(("", self.port), handler)
                break
            except:
                print("address in use, port:", self.port)
                time.sleep(1)

        print("serving files at port", self.port)
        d.serve_forever()



class NodeFileServer(Node):
    def _init(self, path, port, **kwargs):
        path = os.path.normpath(root_path + "/" + path)

        httpserver = HttpServer(path, port)
        httpserver.start()

    """
    def handle_path(self, method, path):
        print("handle path", path, method)

        path = os.path.normpath(root_path + "/" + self.__path + "/" + path)


        file = open(path, "rb")
        data = file.read()
        file.close()

        type = "text/plain"
        if path[-4:] == "html":
            type = "text/html"
        elif path[-2:] == "js":
            type = "application/javascript"
        else:
            type = "application/binary"

        #data = data.encode("utf-8")

        print("return file of {} bytes to path {}".format(len(data), path))

        return type, data
    """


#
# Simple fileserver
# used by http page to load javascript, models, textures
#
from threading import Thread
from http.server import SimpleHTTPRequestHandler


class CORSRequestHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        #path = os.path.dirname(os.path.abspath(__file__))
        #path += "/web"
        path = HttpServer.filepath

        path += self.path
        path = os.path.abspath(path)
        try:
            # Don't allow paths above the root
            if root_path != os.path.commonpath([root_path, path]):
                raise PermissionError("Path outside of root directory")
            file = open(path, 'rb')
            data = file.read()
            file.close()
            status = 200
        except Exception as e:
            print(e.args)
            data = "404 not found".encode()
            status = 404

        self.send_response(status)
        self.send_header("Content-type", "text/html")
        self.send_header("Content-length", len(data))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(data)


