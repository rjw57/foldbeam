import json

import tornado.httpserver
import tornado.ioloop
import tornado.wsgi

from foldbeam.pipeline import Pipeline
from foldbeam.tilestache import TileStacheServerNode
from foldbeam.graph import connect

def main():
    config = json.load(open('pipeline.json'))
    pipeline = Pipeline(config)
    server_node = TileStacheServerNode()
    connect(pipeline.outputs.values()[0], server_node.inputs.raster)

    container = tornado.wsgi.WSGIContainer(server_node.wsgi_server)
    http_server = tornado.httpserver.HTTPServer(container)
    http_server.listen(8888)
    tornado.ioloop.IOLoop.instance().start()

if __name__ == '__main__':
    main()
