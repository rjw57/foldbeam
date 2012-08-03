import SimpleHTTPServer
import SocketServer
import multiprocessing
import os

from tornado.ioloop import IOLoop

from foldbeam.web import restapi

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
    import tornado.wsgi
    application = tornado.wsgi.WSGIContainer(restapi.wsgi_application)
#    application = new_application()
#    application.listen(8888)

    import tornado.netutil
    import tornado.process
    import tornado.httpserver

    server = tornado.httpserver.HTTPServer(application)
    server.bind(8888)
    server.start(0)

#    sockets = tornado.netutil.bind_sockets(8888)
#    tornado.process.fork_processes(0)
#    server = tornado.httpserver.HTTPServer(application)
#    server.add_sockets(sockets)

    IOLoop.instance().start()
