import unittest

import cairo
from osgeo.osr import SpatialReference
import numpy as np

from foldbeam.rendering import core
from foldbeam.rendering.renderer import RendererBase, set_geo_transform

from ..utils import surface_hash, output_surface

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
        renderer.render_callable(self.cr)()
        output_surface(self.surface, 'geo_transform')
        self.assertEqual(surface_hash(self.surface), 3127943)

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
        renderer.render_callable(self.cr)()
        output_surface(self.surface, 'renderer_base')
        self.assertEqual(surface_hash(self.surface), 2986593)

class TestBoundary(unittest.TestCase):
    def test_bbox(self):
        srs = SpatialReference()
        srs.ImportFromEPSG(27700) # British national grid
        uk_area = core.boundary_from_envelope(core.Envelope(0, 700000, 1300000, 0, srs))
        self.assertTrue(uk_area.contains_point(1,1))
        self.assertTrue(uk_area.contains_point(690000,1200000))
        self.assertTrue(uk_area.contains_point(10000, 10000))

        latlng_srs = SpatialReference()
        latlng_srs.ImportFromEPSG(4326) # WGS 84 lat/lng
        uk_latlng = uk_area.transform_to(latlng_srs, 1000, 1.0)
        self.assertTrue(uk_latlng.contains_point(-1.826189, 51.178844)) # Stonehenge
        self.assertTrue(uk_latlng.contains_point(-3.07, 58.64)) # John o'Groats
        self.assertTrue(uk_latlng.contains_point(-5.716111, 50.068611)) # Land's End
        self.assertTrue(uk_latlng.contains_point(-4.333333, 53.283333)) # Anglesey
        self.assertTrue(not uk_latlng.contains_point(-8.47, 51.897222)) # Cork
        self.assertTrue(not uk_latlng.contains_point(2.3508, 48.8567)) # Paris
