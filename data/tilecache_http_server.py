from TileCache.Service import Service, wsgiHandler
from optparse import OptionParser

def run(service, port=8080, threading=False, config=None):
    def app(environ, start_response):
        return wsgiHandler(environ, start_response, service)

    from wsgiref import simple_server
    if threading:
        from SocketServer import ThreadingMixIn
        class myServer(ThreadingMixIn, simple_server.WSGIServer):
            pass 
        httpd = myServer(('',port), simple_server.WSGIRequestHandler,)
    else:    
        httpd = simple_server.WSGIServer(('',port), simple_server.WSGIRequestHandler,)

    httpd.set_app(app)

    try:
        print "Listening on port %s" % port
        httpd.serve_forever()
    except KeyboardInterrupt:
        print "Shutting down."

if __name__ == '__main__':
    from TileCache.Layers.Mapnik import Mapnik
    projection = '+proj=tmerc +lat_0=49 +lon_0=-2 +k=0.9996012717 +x_0=400000 +y_0=-100000 +ellps=airy +datum=OSGB36 +units=m +no_defs'
    bbox = (1393.0196, 13494.9764, 671196.3657, 1230275.0454)
#    projection = '+proj=merc +lon_0=0 +k=1 +x_0=0 +y_0=0 +ellps=WGS84 +datum=WGS84 +units=m +no_defs'
#    bbox = ( -20037508.3428, -15496570.7397, 20037508.3428, 18764656.2314)
    layers = {
        'mapnik': Mapnik('mapnik', 'countries.xml', projection, srs=projection, bbox=bbox),
    }

    from TileCache.Caches.Test import Test as Cache
    srv = Service(Cache(), layers)

    parser = OptionParser()
    parser.add_option("-p", "--port", help="port to run webserver on. Default is 8080", dest="port", action='store', type="int", default=8080)
    parser.add_option("-t", "--threading", help="threading http server. default is false", dest="threading", action='store_true', default=False)
    (options, args) = parser.parse_args()
    run(srv, options.port, options.threading)
