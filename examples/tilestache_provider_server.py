"""A simple example of serving map data for overlay on a web-accessible 'slippy' map.

Run this script and go to http://localhost:8080/.
"""
import logging
import os
import sys

import foldbeam.renderer
from foldbeam.tests.renderer_tests import osm_map_renderer
import selector
import TileStache

logging.basicConfig(level=logging.INFO if '-v' in sys.argv else logging.WARNING)

import httplib2

def url_fetcher(url):
    """A cached version of the default URL fetcher. This function uses filecache to cache the results for 24 hours.
    """
    logging.info('Fetching URL: {0}'.format(url))
    http = httplib2.Http(os.path.join(os.path.dirname(__file__), 'httpcache'))
    rep, content = http.request(url, 'GET')
    if rep.status != 200:
        raise foldbeam.renderer.URLFetchError(str(rep.status) + ' ' + rep.reason)
    return content

cache_path = os.path.join(os.path.dirname(__file__), 'cache')
config = TileStache.Config.buildConfiguration({
    'cache': { 'name': 'Disk', 'path': cache_path } if '--cache' in sys.argv else { 'name': 'Test' },
    'layers': {
        'test': {
            'provider': {
                'class': 'foldbeam.goodies.tilestache:TileStacheProvider',
                'kwargs': { },
            },
#                'projection': 'WGS84',
        },
    },
})

#renderer = foldbeam.renderer.TileFetcher(url_fetcher=url_fetcher)
renderer = osm_map_renderer(url_fetcher=url_fetcher, use_tile_fetcher=False)
config.layers['test'].provider.renderer = renderer

tile_app = TileStache.WSGITileServer(config)

index = open(os.path.join(os.path.dirname(__file__), 'leaflet-example.html')).read()
def index_app(environ, start_response):
    start_response('200 OK', [('Content-Type', 'text/html'), ('Content-Length', str(len(index)))])
    return [index]

app = selector.Selector()
app.parser = lambda x: x
app.add('^/$', GET=index_app)
app.add('^/', GET=tile_app)

if __name__ == '__main__':
    #from wsgiutils import wsgiServer
    #wsgiServer.WSGIServer(('localhost', 8080), {'/': app}).serve_forever()

    from wsgiref import simple_server
    simple_server.make_server('localhost', 8080, app).serve_forever()

