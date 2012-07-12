import unittest

import cairo

from foldbeam.core import RendererBase, set_geo_transform
from foldbeam.tests import surface_hash, output_surface

class TestGeoTransform(unittest.TestCase):
    def setUp(self):
        # Create a cairo image surface
        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 640, 480)
        self.cr = cairo.Context(self.surface)

    def test_set_geo_transform(self):
        self.assertEqual(self.cr.clip_extents(), (0.0, 0.0, 640.0, 480.0))
        set_geo_transform(self.cr, 49, 51, 2, 1, 640, 480)
        self.assertEqual(self.cr.clip_extents(), (49.0, 1.0, 51.0, 2.0))
        renderer = RendererBase()
        renderer.render(self.cr)
        self.surface.write_to_png('foo.png')

class TestCore(unittest.TestCase):
    def setUp(self):
        # Create a cairo image surface
        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 640, 480)
        self.cr = cairo.Context(self.surface)
        self.cr.set_source_rgba(0,0,0,0)
        self.cr.paint()

        set_geo_transform(self.cr, 49, 51, 2, 1, 400, 200)

    def test_render(self):
        renderer = RendererBase()
        renderer.render(self.cr)
        output_surface(self.surface, 'renderer_base')
        self.assertEqual(surface_hash(self.surface), 2986593)
