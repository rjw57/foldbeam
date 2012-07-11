import unittest

import cairo

from foldbeam.core import set_geo_transform
from foldbeam.renderer import TileFetcher

class TestTileFetcher(unittest.TestCase):
    def setUp(self):
        # Create a cairo image surface
        sw, sh = (640, 480)
        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, sw, sh)
        self.cr = cairo.Context(self.surface)
        self.cr.set_source_rgba(0,0,0,0)
        self.cr.paint()

        # The EPSG:3857 co-ordinates of Big Ben, an easily identifiable landmark
        cx, cy = (-13871.6330672413, 6710328.3443702850)
        width = 0.5e3 # 500m
        height = float(width * sh) / float(sw)
        set_geo_transform(self.cr, cx-0.5*width, cx+0.5*width, cy+0.5*height, cy-0.5*height, sw, sh)

    def test_default(self):
        renderer = TileFetcher()
        renderer.render(self.cr)
        self.surface.write_to_png('tile-fetcher-default.png')

