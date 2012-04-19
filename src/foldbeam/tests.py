import _gdal
import core
import graph
import nodes
import math
from osgeo import gdal
from osgeo.osr import SpatialReference
import pads
from TileStache.Config import buildConfiguration
import os
import unittest

class TestUtility(unittest.TestCase):
    def test_create_render_dataset(self):
        srs = SpatialReference()
        srs.ImportFromEPSG(4326) # WGS84 lat/lng

        r1 = _gdal.create_render_dataset(core.Envelope(0,0,1,1, srs), (256, 128))
        self.assertIsNotNone(r1)
        self.assertIsNotNone(r1.dataset)
        self.assertEqual(r1.dataset.RasterXSize, 256)
        self.assertEqual(r1.dataset.RasterYSize, 128)

class TestTileStacheRasterNode(unittest.TestCase):
    def setUp(self):
        cache_dir = os.path.join(os.getcwd(), 'tilestache')
        self.config = buildConfiguration({
            'cache': {
                'name': 'Disk',
                'path': cache_dir,
            },
            'layers': {
                'osm': {
                    'provider': {
                        'name': 'proxy', 
                        'url': 'http://otile1.mqcdn.com/tiles/1.0.0/osm/{Z}/{X}/{Y}.png',
                    },
                },
                'aerial': {
                    'provider': {
                        'name': 'proxy', 
                        'provider': 'MICROSOFT_AERIAL',
                    },
                },
            },
        })

        self.big_ben_os = (530269, 179640)

    def test_tilestache_lat_lng(self):
        envelope_srs = SpatialReference()
        envelope_srs.ImportFromEPSG(4326) # WGS 84 lat/lng
        envelope = core.Envelope(-180, 180, 89, -89, envelope_srs)

        node = nodes.TileStacheRasterNode(self.config.layers['osm'])
        size = (1024, 512)
        t, raster = node.outputs['raster'](envelope, size)
        self.assertEqual(t, pads.ContentType.RASTER)
        self.assertEqual(raster.array.shape[1], size[0])
        self.assertEqual(raster.array.shape[0], size[1])

        ds = raster.as_dataset()
        self.assertEqual(ds.RasterXSize, size[0])
        self.assertEqual(ds.RasterYSize, size[1])
        raster.write_tiff('world-latlng.tiff')

    def test_tilestache_usna(self):
        envelope_srs = SpatialReference()
        envelope_srs.ImportFromEPSG(2163) # US National Atlas Equal Area
        envelope = core.Envelope(-3e6, 3e6, 2e6, -2e6, envelope_srs)

        node = nodes.TileStacheRasterNode(self.config.layers['osm'])
        size = (1200, 800)
        t, raster = node.outputs['raster'](envelope, size)
        self.assertEqual(t, pads.ContentType.RASTER)
        self.assertEqual(raster.array.shape[1], size[0])
        self.assertEqual(raster.array.shape[0], size[1])

        ds = raster.as_dataset()
        self.assertEqual(ds.RasterXSize, size[0])
        self.assertEqual(ds.RasterYSize, size[1])
        raster.write_tiff('world-usna.tiff')

    def test_tilestache_osgrid_overlay(self):
        envelope_srs = SpatialReference()
        envelope_srs.ImportFromEPSG(27700) # British national grid
        envelope = core.Envelope(0, 700000, 1300000, 0, envelope_srs)

        roads_node = nodes.TileStacheRasterNode(self.config.layers['osm'])
        aerial_node = nodes.TileStacheRasterNode(self.config.layers['aerial'])
        node = nodes.LayerRasterNode(
            [x.outputs['raster'] for x in (aerial_node, roads_node)],
            (1, 0.5),
        )

        size = (700, 1300)
        t, raster = node.outputs['raster'](envelope, size)
        self.assertEqual(t, pads.ContentType.RASTER)
        self.assertEqual(raster.array.shape[1], size[0])
        self.assertEqual(raster.array.shape[0], size[1])

        ds = raster.as_dataset()
        self.assertEqual(ds.RasterXSize, size[0])
        self.assertEqual(ds.RasterYSize, size[1])
        raster.write_tiff('uk-osgrid-overlay.tiff')

    def test_tilestache_osgrid(self):
        envelope_srs = SpatialReference()
        envelope_srs.ImportFromEPSG(27700) # British national grid
        envelope = core.Envelope(0, 700000, 1300000, 0, envelope_srs)

        node = nodes.TileStacheRasterNode(self.config.layers['osm'])
        size = (700, 1300)
        t, raster = node.outputs['raster'](envelope, size)
        self.assertEqual(t, pads.ContentType.RASTER)
        self.assertEqual(raster.array.shape[1], size[0])
        self.assertEqual(raster.array.shape[0], size[1])

        ds = raster.as_dataset()
        self.assertEqual(ds.RasterXSize, size[0])
        self.assertEqual(ds.RasterYSize, size[1])
        raster.write_tiff('uk-osgrid.tiff')

    def test_tilestache_osgrid_crazy(self):
        envelope_srs = SpatialReference()
        envelope_srs.ImportFromEPSG(27700) # British national grid
        envelope = core.Envelope(-2e6, 2e6, 3e6, -3e6, envelope_srs)

        node = nodes.TileStacheRasterNode(self.config.layers['osm'])
        size = (800, 1200)
        t, raster = node.outputs['raster'](envelope, size)
        self.assertEqual(t, pads.ContentType.RASTER)
        self.assertEqual(raster.array.shape[1], size[0])
        self.assertEqual(raster.array.shape[0], size[1])

        ds = raster.as_dataset()
        self.assertEqual(ds.RasterXSize, size[0])
        self.assertEqual(ds.RasterYSize, size[1])
        raster.write_tiff('mad-osgrid.tiff')

    def test_tilestache_big_ben(self):
        # square around Big Ben
        skirt = 300 # metres
        centre = self.big_ben_os

        envelope_srs = SpatialReference()
        envelope_srs.ImportFromEPSG(27700) # British national grid
        envelope = core.Envelope(
                centre[0]-0.5*skirt, centre[0]+0.5*skirt, centre[1]+0.5*skirt, centre[1]-0.5*skirt,
                envelope_srs)

        node = nodes.TileStacheRasterNode(self.config.layers['osm'])
        size = (512, 512)
        t, raster = node.outputs['raster'](envelope, size)
        self.assertEqual(t, pads.ContentType.RASTER)
        self.assertEqual(raster.array.shape[1], size[0])
        self.assertEqual(raster.array.shape[0], size[1])

        ds = raster.as_dataset()
        self.assertEqual(ds.RasterXSize, size[0])
        self.assertEqual(ds.RasterYSize, size[1])
        raster.write_tiff('big-ben.tiff')

    def test_tilestache_big_ben_small(self):
        # square around Big Ben
        skirt = 100 # metres
        centre = self.big_ben_os

        envelope_srs = SpatialReference()
        envelope_srs.ImportFromEPSG(27700) # British national grid
        envelope = core.Envelope(
                centre[0]-0.5*skirt, centre[0]+0.5*skirt, centre[1]+0.5*skirt, centre[1]-0.5*skirt,
                envelope_srs)

        node = nodes.TileStacheRasterNode(self.config.layers['osm'])
        size = (512, 512)
        t, raster = node.outputs['raster'](envelope, size)
        self.assertEqual(t, pads.ContentType.RASTER)
        self.assertEqual(raster.array.shape[1], size[0])
        self.assertEqual(raster.array.shape[0], size[1])

        ds = raster.as_dataset()
        self.assertEqual(ds.RasterXSize, size[0])
        self.assertEqual(ds.RasterYSize, size[1])
        raster.write_tiff('big-ben-sm.tiff')

    def test_tilestache_big_ben_proj_units(self):
        # test letting image size be determined from projection units

        # square around Big Ben
        skirt = (300, 100) # metres
        centre = self.big_ben_os

        envelope_srs = SpatialReference()
        envelope_srs.ImportFromEPSG(27700) # British national grid
        envelope = core.Envelope(
                centre[0]-0.5*skirt[0], centre[0]+0.5*skirt[0], centre[1]+0.5*skirt[1], centre[1]-0.5*skirt[1],
                envelope_srs)

        node = nodes.TileStacheRasterNode(self.config.layers['osm'])
        t, raster = node.outputs['raster'](envelope)
        self.assertEqual(t, pads.ContentType.RASTER)
        self.assertEqual(raster.array.shape[1], skirt[0])
        self.assertEqual(raster.array.shape[0], skirt[1])

        ds = raster.as_dataset()
        self.assertEqual(ds.RasterXSize, skirt[0])
        self.assertEqual(ds.RasterYSize, skirt[1])
        raster.write_tiff('big-ben-metres.tiff')

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

class TestOutputPad(unittest.TestCase):
    def setUp(self):
        self.bng_srs = SpatialReference()
        self.bng_srs.ImportFromEPSG(27700) # British national grid

    def test_damage(self):
        damages = []
        def damage_cb(d):
            damages.append(d)

        e = pads.OutputPad()
        e.damaged.connect(damage_cb)

        self.assertEqual(len(damages), 0)
        env1 = core.Envelope(0,0,1,1,self.bng_srs)
        self.assertIsNotNone(env1)
        env2 = core.Envelope(0,0,2,2,self.bng_srs)
        self.assertIsNotNone(env2)

        e.notify_damage(env1)
        self.assertEqual(len(damages), 1)
        self.assertEqual(damages[-1], env1)
        self.assertNotEqual(damages[-1], env2)

        e.notify_damage(env2)
        self.assertEqual(len(damages), 2)
        self.assertEqual(damages[-1], env2)
        self.assertNotEqual(damages[-1], env1)

        e.damaged.disconnect(damage_cb)
        e.notify_damage(env1)
        self.assertEqual(len(damages), 2)
        self.assertEqual(damages[-1], env2)
        self.assertNotEqual(damages[-1], env1)

def test_suite():
    return unittest.TestSuite([
        unittest.makeSuite(TestUtility),
        unittest.makeSuite(TestTileStacheRasterNode),
        unittest.makeSuite(TestBoundary),
        unittest.makeSuite(TestOutputPad),
    ])
