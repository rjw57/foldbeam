import SimpleHTTPServer
import SocketServer
import multiprocessing
import os

from tornado.ioloop import IOLoop

from foldbeam.web.restapi import new_application

def static_file_server():
    webui_dir = os.path.join(os.path.dirname(__file__), 'output')
    os.chdir(webui_dir)
    handler = SimpleHTTPServer.SimpleHTTPRequestHandler
    httpd = SocketServer.TCPServer(('0.0.0.0', 8000), handler)
    print('Serving UI at http://0.0.0.0:8000')
    httpd.serve_forever()

if __name__ == '__main__':
    p = multiprocessing.Process(target=static_file_server)
    p.daemon = True
    p.start()

    print('Serving API at http://0.0.0.0:8888')
    application = new_application()
    application.listen(8888)
    IOLoop.instance().start()
