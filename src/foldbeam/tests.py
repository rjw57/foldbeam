import _gdal
from core import Envelope
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

        r1 = _gdal.create_render_dataset(Envelope(0,0,1,1), srs, (256, 128))
        self.assertIsNotNone(r1)
        self.assertEqual(r1.RasterXSize, 256)
        self.assertEqual(r1.RasterYSize, 128)

    def test_transform_envelope(self):
        # 200m x 200m square around stonehenge
        envelope = Envelope(412148-100, 412148+100, 142251+100, 142251-100)

        src_srs = SpatialReference()
        src_srs.ImportFromEPSG(27700) # British national grid

        dst_srs = SpatialReference()
        dst_srs.ImportFromEPSG(4326) # WGS84 lat/lng

        # Identity transform
        self.assertEqual(envelope, _gdal.transform_envelope(envelope, src_srs, src_srs))

        # Test that latitude and longitude of stonehenge is within transformed envelope
        lnglat_envelope = _gdal.transform_envelope(envelope, src_srs, dst_srs)
        self.assertNotEqual(envelope, lnglat_envelope)
        self.assertTrue(-1.826189 > lnglat_envelope.left)
        self.assertTrue(-1.826189 < lnglat_envelope.right)
        self.assertTrue(51.178844 > lnglat_envelope.top)
        self.assertTrue(51.178844 < lnglat_envelope.bottom)

class TestRasterNode(unittest.TestCase):
    def test_create_node(self):
        n = nodes.RasterNode()
        #default_srs = SpatialReference()
        #default_srs.ImportFromEPSG(3857)
        #self.assertTrue(default_srs.IsSame(n.srs))

    def test_render_node(self):
        envelope = Envelope(369475, 369475 + 1429*50, 205525, 205525 + 1887*-50)
        envelope_srs = SpatialReference()
        envelope_srs.ImportFromEPSG(27700) # British national grid

        node = nodes.RasterNode()
        raster = node.render(envelope, envelope_srs, (256, 256))
        self.assertEqual(raster.RasterXSize, 256)
        self.assertEqual(raster.RasterYSize, 256)

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

    def test_tilestache_lat_lng(self):
        envelope = Envelope(-180, 180, 89, -89)
        envelope_srs = SpatialReference()
        envelope_srs.ImportFromEPSG(4326) # WGS 84 lat/lng

        node = nodes.TileStacheRasterNode(self.config.layers['osm'])
        size = (1024, 512)
        raster = node.render(envelope, envelope_srs, size)
        self.assertEqual(raster.RasterXSize, size[0])
        self.assertEqual(raster.RasterYSize, size[1])

        driver = gdal.GetDriverByName('GTiff')
        driver.CreateCopy('world-latlng.tiff', raster)

    def test_tilestache_usna(self):
        envelope = Envelope(-3e6, 3e6, 2e6, -2e6)
        envelope_srs = SpatialReference()
        envelope_srs.ImportFromEPSG(2163) # US National Atlas Equal Area

        node = nodes.TileStacheRasterNode(self.config.layers['osm'])
        size = (1200, 800)
        raster = node.render(envelope, envelope_srs, size)
        self.assertEqual(raster.RasterXSize, size[0])
        self.assertEqual(raster.RasterYSize, size[1])

        driver = gdal.GetDriverByName('GTiff')
        driver.CreateCopy('world-usna.tiff', raster)

    def test_tilestache_osgrid(self):
        envelope = Envelope(0, 700000, 1300000, 0)
        envelope_srs = SpatialReference()
        envelope_srs.ImportFromEPSG(27700) # British national grid

        node = nodes.TileStacheRasterNode(self.config.layers['osm'])
        size = (700, 1300)
        raster = node.render(envelope, envelope_srs, size)
        self.assertEqual(raster.RasterXSize, size[0])
        self.assertEqual(raster.RasterYSize, size[1])

        driver = gdal.GetDriverByName('GTiff')
        driver.CreateCopy('uk-osgrid.tiff', raster)

    def test_tilestache_osgrid_crazy(self):
        envelope = Envelope(-2e6, 2e6, 3e6, -3e6)
        envelope_srs = SpatialReference()
        envelope_srs.ImportFromEPSG(27700) # British national grid

        node = nodes.TileStacheRasterNode(self.config.layers['osm'])
        size = (800, 1200)
        raster = node.render(envelope, envelope_srs, size)
        self.assertEqual(raster.RasterXSize, size[0])
        self.assertEqual(raster.RasterYSize, size[1])

        driver = gdal.GetDriverByName('GTiff')
        driver.CreateCopy('mad-osgrid.tiff', raster)

    def test_tilestache_big_ben(self):
        # square around Big Ben
        skirt = 300 # metres
        centre = (530269, 179630)
        envelope = Envelope(centre[0]-0.5*skirt, centre[0]+0.5*skirt, centre[1]+0.5*skirt, centre[1]-0.5*skirt)

        envelope_srs = SpatialReference()
        envelope_srs.ImportFromEPSG(27700) # British national grid

        node = nodes.TileStacheRasterNode(self.config.layers['osm'])
        size = (512, 512)
        raster = node.render(envelope, envelope_srs, size)
        self.assertEqual(raster.RasterXSize, size[0])
        self.assertEqual(raster.RasterYSize, size[1])

        driver = gdal.GetDriverByName('GTiff')
        driver.CreateCopy('big-ben.tiff', raster)

def test_suite():
    return unittest.TestSuite([
        unittest.makeSuite(TestUtility),
        unittest.makeSuite(TestRasterNode),
        unittest.makeSuite(TestTileStacheRasterNode),
    ])
