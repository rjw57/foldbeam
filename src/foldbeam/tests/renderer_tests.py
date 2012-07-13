import hashlib
import logging
import StringIO
import unittest

import cairo
from filecache import filecache
from osgeo.osr import SpatialReference

from foldbeam.core import set_geo_transform
from foldbeam.renderer import TileFetcher, default_url_fetcher, TileStacheProvider
from foldbeam.tests import surface_hash, output_surface

import TileStache

@filecache(24*60*60)
def test_url_fetcher(url):
    """A cached version of the default URL fetcher. This function uses filecache to cache the results for 24 hours.
    """
    logging.info('Fetching URL: {0}'.format(url))
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

    def centre_on_hawaii(self, width=500):
        # The EPSG:3857 co-ordinates of Hawaii
        cx, cy = (-17565813.6724973172, 2429047.3665894675)
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
        self.assertEqual(surface_hash(self.surface)/10, 723002)

    def test_aerial(self):
        self.centre_on_big_ben(1000e3)
        renderer = TileFetcher(
            url_pattern='http://oatile1.mqcdn.com/tiles/1.0.0/sat/{zoom}/{x}/{y}.jpg',
            url_fetcher=test_url_fetcher
        )
        renderer.render(self.cr)
        output_surface(self.surface, 'tilefetcher_aerial')
        self.assertEqual(surface_hash(self.surface)/10, 720869)

    def test_aerial_hawaii(self):
        # should be a large enough area to wrap over the -180/180 longitude
        self.centre_on_hawaii(7000e3) # 7000 km
        renderer = TileFetcher(
            url_pattern='http://oatile1.mqcdn.com/tiles/1.0.0/sat/{zoom}/{x}/{y}.jpg',
            url_fetcher=test_url_fetcher
        )
        renderer.render(self.cr)
        output_surface(self.surface, 'tilefetcher_aerial_hawaii')
        self.assertEqual(surface_hash(self.surface)/10, 545209)

    def test_british_national_grid(self):
        sw = int(671196.3657 - 1393.0196) / 1000
        sh = int(1230275.0454 - 13494.9764) / 1000
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, sw, sh)
        cr = cairo.Context(surface)

        # The valid range of the British national grid
        set_geo_transform(cr,
            1393.0196, 671196.3657, 1230275.0454, 13494.9764,
            surface.get_width(), surface.get_height()
        )

        srs = SpatialReference()
        srs.ImportFromEPSG(27700) # OSGB 1936

        renderer = TileFetcher(url_fetcher=test_url_fetcher)
        renderer.render(cr, spatial_reference=srs)
        output_surface(surface, 'tilefetcher_british_national_grid')
        self.assertEqual(surface_hash(surface)/10, 1879583)

    def test_british_national_grid_upside_down(self):
        sw = int(671196.3657 - 1393.0196) / 1000
        sh = int(1230275.0454 - 13494.9764) / 1000
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, sw, sh)
        cr = cairo.Context(surface)

        # The valid range of the British national grid_upside_down
        set_geo_transform(cr,
            1393.0196, 671196.3657, 13494.9764, 1230275.0454,
            surface.get_width(), surface.get_height()
        )

        srs = SpatialReference()
        srs.ImportFromEPSG(27700) # OSGB 1936

        renderer = TileFetcher(url_fetcher=test_url_fetcher)
        renderer.render(cr, spatial_reference=srs)
        output_surface(surface, 'tilefetcher_british_national_grid_upside_down')
        self.assertEqual(surface_hash(surface)/10, 1879583)

    def test_british_national_grid_mirrored(self):
        sw = int(671196.3657 - 1393.0196) / 1000
        sh = int(1230275.0454 - 13494.9764) / 1000
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, sw, sh)
        cr = cairo.Context(surface)

        # The valid range of the British national grid_mirrored
        set_geo_transform(cr,
            671196.3657, 1393.0196, 1230275.0454, 13494.9764,
            surface.get_width(), surface.get_height()
        )

        srs = SpatialReference()
        srs.ImportFromEPSG(27700) # OSGB 1936

        renderer = TileFetcher(url_fetcher=test_url_fetcher)
        renderer.render(cr, spatial_reference=srs)
        output_surface(surface, 'tilefetcher_british_national_grid_mirrored')
        self.assertEqual(surface_hash(surface)/10, 1879583)

    def test_british_national_grid_wide(self):
        sw = 1200
        sh = 900
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, sw, sh)
        cr = cairo.Context(surface)

        # The valid range of the British national grid
        set_geo_transform(cr,
            -2400000, 2400000, 1800000, -1800000,
            surface.get_width(), surface.get_height()
        )

        srs = SpatialReference()
        srs.ImportFromEPSG(27700) # OSGB 1936

        renderer = TileFetcher(url_fetcher=test_url_fetcher)
        renderer.render(cr, spatial_reference=srs)
        output_surface(surface, 'tilefetcher_british_national_grid_wide')
        self.assertEqual(surface_hash(surface)/10, 2558175)

    def test_british_national_grid_ultra_wide(self):
        sw = 1200
        sh = 900
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, sw, sh)
        cr = cairo.Context(surface)

        # The valid range of the British national grid
        set_geo_transform(cr,
            -4800000, 4800000, 3600000, -3600000,
            surface.get_width(), surface.get_height()
        )

        srs = SpatialReference()
        srs.ImportFromEPSG(27700) # OSGB 1936

        renderer = TileFetcher(url_fetcher=test_url_fetcher)
        renderer.render(cr, spatial_reference=srs)
        output_surface(surface, 'tilefetcher_british_national_grid_ultra_wide')
        self.assertEqual(surface_hash(surface)/10, 2648355)

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
