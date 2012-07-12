import logging
import unittest

import cairo

from foldbeam.core import set_geo_transform
from foldbeam.renderer import TileFetcher, default_url_fetcher
from foldbeam.tests import surface_hash, output_surface

def test_url_fetcher(url):
    """The default URL fetcher to use in :py:class:`TileFetcher`. If there is an error fetching the URL a URLFetchError
    is raised.

    """
    logging.info('Intercepted attempt to load URL: {0}'.format(url))
    return default_url_fetcher(url)

class TestTileFetcher(unittest.TestCase):
    def setUp(self):
        # Create a cairo image surface
        sw, sh = (640, 480)
        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, sw, sh)
        self.cr = cairo.Context(self.surface)
        self.cr.set_source_rgba(0,0,0,0)
        self.cr.paint()

    def centre_on_big_ben(self, width=500):
        # The EPSG:3857 co-ordinates of Big Ben, an easily identifiable landmark
        cx, cy = (-13871.6330672413, 6710328.3443702850)
        height = float(width * self.surface.get_height()) / float(self.surface.get_width())
        set_geo_transform(
                self.cr,
                cx-0.5*width, cx+0.5*width, cy+0.5*height, cy-0.5*height,
                self.surface.get_width(), self.surface.get_height())

    def test_default(self):
        self.centre_on_big_ben()
        renderer = TileFetcher(url_fetcher=test_url_fetcher)
        renderer.render(self.cr)
        output_surface(self.surface, 'tilefetcher_default')
        self.assertEqual(surface_hash(self.surface)/10, 782746)

    def test_aerial(self):
        self.centre_on_big_ben(1000e3)
        renderer = TileFetcher(
            url_pattern='http://oatile1.mqcdn.com/tiles/1.0.0/sat/{zoom}/{x}/{y}.jpg',
            url_fetcher=test_url_fetcher
        )
        renderer.render(self.cr)
        output_surface(self.surface, 'tilefetcher_aerial')
        self.assertEqual(surface_hash(self.surface)/10, 722896)

