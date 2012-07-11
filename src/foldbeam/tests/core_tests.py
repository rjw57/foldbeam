import unittest

import cairo

from foldbeam.core import RendererBase

class TestCore(unittest.TestCase):
    def setUp(self):
        # Create a cairo image surface
        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 640, 480)
        self.cr = cairo.Context(self.surface)
        self.cr.set_source_rgba(0,0,0,0)
        self.cr.paint()

    def test_render(self):
        renderer = RendererBase()
        renderer.render(self.cr)
        self.surface.write_to_png('foo.png')
