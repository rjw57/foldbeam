import _gdal
import core
import nodes
import math
from osgeo import gdal
from osgeo.osr import SpatialReference
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

class TestRasterNode(unittest.TestCase):
    def test_create_node(self):
        n = nodes.RasterNode()

    def test_render_node(self):
        envelope_srs = SpatialReference()
        envelope_srs.ImportFromEPSG(27700) # British national grid
        envelope = core.Envelope(369475, 369475 + 1429*50, 205525, 205525 + 1887*-50, envelope_srs)

        node = nodes.RasterNode()
        raster = node.render(envelope, (256, 256))
        self.assertEqual(raster.dataset.RasterXSize, 256)
        self.assertEqual(raster.dataset.RasterYSize, 256)

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
            },
        })

        self.big_ben_os = (530269, 179640)

    def test_tilestache_lat_lng(self):
        envelope_srs = SpatialReference()
        envelope_srs.ImportFromEPSG(4326) # WGS 84 lat/lng
        envelope = core.Envelope(-180, 180, 89, -89, envelope_srs)

        node = nodes.TileStacheRasterNode(self.config.layers['osm'])
        size = (1024, 512)
        raster = node.render(envelope, size)
        self.assertEqual(raster.dataset.RasterXSize, size[0])
        self.assertEqual(raster.dataset.RasterYSize, size[1])

        driver = gdal.GetDriverByName('GTiff')
        driver.CreateCopy('world-latlng.tiff', raster.dataset)

    def test_tilestache_usna(self):
        envelope_srs = SpatialReference()
        envelope_srs.ImportFromEPSG(2163) # US National Atlas Equal Area
        envelope = core.Envelope(-3e6, 3e6, 2e6, -2e6, envelope_srs)

        node = nodes.TileStacheRasterNode(self.config.layers['osm'])
        size = (1200, 800)
        raster = node.render(envelope, size)
        self.assertEqual(raster.dataset.RasterXSize, size[0])
        self.assertEqual(raster.dataset.RasterYSize, size[1])

        driver = gdal.GetDriverByName('GTiff')
        driver.CreateCopy('world-usna.tiff', raster.dataset)

    def test_tilestache_osgrid(self):
        envelope_srs = SpatialReference()
        envelope_srs.ImportFromEPSG(27700) # British national grid
        envelope = core.Envelope(0, 700000, 1300000, 0, envelope_srs)

        node = nodes.TileStacheRasterNode(self.config.layers['osm'])
        size = (700, 1300)
        raster = node.render(envelope, size)
        self.assertEqual(raster.dataset.RasterXSize, size[0])
        self.assertEqual(raster.dataset.RasterYSize, size[1])

        driver = gdal.GetDriverByName('GTiff')
        driver.CreateCopy('uk-osgrid.tiff', raster.dataset)

    def test_tilestache_osgrid_crazy(self):
        envelope_srs = SpatialReference()
        envelope_srs.ImportFromEPSG(27700) # British national grid
        envelope = core.Envelope(-2e6, 2e6, 3e6, -3e6, envelope_srs)

        node = nodes.TileStacheRasterNode(self.config.layers['osm'])
        size = (800, 1200)
        raster = node.render(envelope, size)
        self.assertEqual(raster.dataset.RasterXSize, size[0])
        self.assertEqual(raster.dataset.RasterYSize, size[1])

        driver = gdal.GetDriverByName('GTiff')
        driver.CreateCopy('mad-osgrid.tiff', raster.dataset)

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
        raster = node.render(envelope, size)
        self.assertEqual(raster.dataset.RasterXSize, size[0])
        self.assertEqual(raster.dataset.RasterYSize, size[1])

        driver = gdal.GetDriverByName('GTiff')
        driver.CreateCopy('big-ben.tiff', raster.dataset)

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
        raster = node.render(envelope, size)
        self.assertEqual(raster.dataset.RasterXSize, size[0])
        self.assertEqual(raster.dataset.RasterYSize, size[1])

        driver = gdal.GetDriverByName('GTiff')
        driver.CreateCopy('big-ben-sm.tiff', raster.dataset)

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

def test_suite():
    return unittest.TestSuite([
        unittest.makeSuite(TestUtility),
        unittest.makeSuite(TestRasterNode),
        unittest.makeSuite(TestTileStacheRasterNode),
        unittest.makeSuite(TestBoundary),
    ])
