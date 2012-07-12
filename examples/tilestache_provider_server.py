import logging

import foldbeam.renderer
import TileStache

logging.basicConfig(level=logging.INFO)

from filecache import filecache
@filecache(24*60*60)
def test_url_fetcher(url):
    """A cached version of the default URL fetcher. This function uses filecache to cache the results for 24 hours.
    """
    logging.info('Fetching URL: {0}'.format(url))
    return foldbeam.renderer.default_url_fetcher(url)

def main():
    config = TileStache.Config.buildConfiguration({
        'cache': { 'name': 'Test' },
        'layers': {
            'test': {
                'provider': {
                    'class': 'foldbeam.renderer:TileStacheProvider',
                    'kwargs': { },
                },
#                'projection': 'WGS84',
            },
        },
    })

    config.layers['test'].provider.renderer = foldbeam.renderer.TileFetcher(url_fetcher=test_url_fetcher)

    app = TileStache.WSGITileServer(config)

    from wsgiutils import wsgiServer
    print('About to start serving. Try visiting http://localhost:8080/test/')
    wsgiServer.WSGIServer(('localhost', 8080), {'/': app}).serve_forever()

if __name__ == '__main__':
    main()

