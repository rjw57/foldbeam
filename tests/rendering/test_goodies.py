import StringIO
import unittest

import TileStache

from foldbeam.rendering.goodies.tilestache import TileStacheProvider

class TestTileStacheProvider(unittest.TestCase):
    def setUp(self):
        self.config = TileStache.Config.Configuration(cache=TileStache.Caches.Test(), dirpath='')

    def test_default(self):
        self.config.layers['test'] = TileStache.Core.Layer(
                self.config,
                TileStache.Geography.SphericalMercator(),
                TileStache.Core.Metatile())
        provider = TileStacheProvider(self.config.layers['test'])
        self.config.layers['test'].provider = provider

        app = TileStache.WSGITileServer(self.config)
        def start_response(status, response_headers, exc_info=None):
            self.assertEqual(status, '200 OK')
            return None

        environ = {
            'REQUEST_METHOD': 'GET',
            'SCRIPT_NAME': '/',
            'PATH_INFO': '/test/2/2/2.png',
            'QUERY_STRING': '',
        }

        output = StringIO.StringIO()
        [output.write(x) for x in app(environ, start_response)]

        # use the approximate length of output as a measure of entropy
        self.assertEqual(len(output.getvalue())/10, 5212)

