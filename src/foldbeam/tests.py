import datetime
import logging
import math
import os
import unittest
import sys

import numpy as np
from osgeo import gdal
from osgeo.osr import SpatialReference
from TileStache.Config import buildConfiguration
import zmq
from zmq.eventloop.ioloop import IOLoop, ZMQPoller

from foldbeam import core, graph, _gdal, network
from foldbeam import raster, vector, tilestache

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

        node = raster.TileStacheSource(config=self.config)
        size = (1024, 512)
        tile = node.outputs.osm(envelope=envelope, size=size)
        self.assertIsNotNone(tile)
        self.assertIsInstance(tile, raster.Raster)
        self.assertEqual(tile.array.shape[1], size[0])
        self.assertEqual(tile.array.shape[0], size[1])

        ds = tile.as_dataset()
        self.assertEqual(ds.RasterXSize, size[0])
        self.assertEqual(ds.RasterYSize, size[1])
        tile.write_tiff('world-latlng.tiff')

    def test_tilestache_usna(self):
        envelope_srs = SpatialReference()
        envelope_srs.ImportFromEPSG(2163) # US National Atlas Equal Area
        envelope = core.Envelope(-3e6, 3e6, 2e6, -2e6, envelope_srs)

        node = raster.TileStacheSource(config=self.config)
        size = (1200, 800)
        tile = node.outputs.osm(envelope=envelope, size=size)
        self.assertIsNotNone(tile)
        self.assertIsInstance(tile, raster.Raster)
        self.assertEqual(tile.array.shape[1], size[0])
        self.assertEqual(tile.array.shape[0], size[1])

        ds = tile.as_dataset()
        self.assertEqual(ds.RasterXSize, size[0])
        self.assertEqual(ds.RasterYSize, size[1])
        tile.write_tiff('world-usna.tiff')

    def test_tilestache_osgrid_overlay(self):
        envelope_srs = SpatialReference()
        envelope_srs.ImportFromEPSG(27700) # British national grid
        envelope = core.Envelope(0, 700000, 1300000, 0, envelope_srs)

        ts_node = raster.TileStacheSource(config=self.config)
        node = raster.CompositeOver(top_opacity=0.5)
        graph.connect(ts_node.outputs.osm, node.inputs.top)
        graph.connect(ts_node.outputs.aerial, node.inputs.bottom)

        size = (700, 1300)
        tile = node.outputs.output(envelope=envelope, size=size)
        self.assertIsNotNone(tile)
        self.assertIsInstance(tile, raster.Raster)
        self.assertEqual(tile.array.shape[1], size[0])
        self.assertEqual(tile.array.shape[0], size[1])

        ds = tile.as_dataset()
        self.assertEqual(ds.RasterXSize, size[0])
        self.assertEqual(ds.RasterYSize, size[1])
        tile.write_tiff('uk-osgrid-overlay.tiff')

    def test_tilestache_osgrid(self):
        envelope_srs = SpatialReference()
        envelope_srs.ImportFromEPSG(27700) # British national grid
        envelope = core.Envelope(0, 700000, 1300000, 0, envelope_srs)

        node = raster.TileStacheSource(config=self.config)
        size = (700, 1300)
        tile = node.outputs.osm(envelope=envelope, size=size)
        self.assertIsNotNone(tile)
        self.assertIsInstance(tile, raster.Raster)
        self.assertEqual(tile.array.shape[1], size[0])
        self.assertEqual(tile.array.shape[0], size[1])

        ds = tile.as_dataset()
        self.assertEqual(ds.RasterXSize, size[0])
        self.assertEqual(ds.RasterYSize, size[1])
        tile.write_tiff('uk-osgrid.tiff')

    def test_tilestache_osgrid_crazy(self):
        envelope_srs = SpatialReference()
        envelope_srs.ImportFromEPSG(27700) # British national grid
        envelope = core.Envelope(-2e6, 2e6, 3e6, -3e6, envelope_srs)

        node = raster.TileStacheSource(config=self.config)
        size = (800, 1200)
        tile = node.outputs.osm(envelope=envelope, size=size)
        self.assertIsNotNone(tile)
        self.assertIsInstance(tile, raster.Raster)
        self.assertEqual(tile.array.shape[1], size[0])
        self.assertEqual(tile.array.shape[0], size[1])

        ds = tile.as_dataset()
        self.assertEqual(ds.RasterXSize, size[0])
        self.assertEqual(ds.RasterYSize, size[1])
        tile.write_tiff('mad-osgrid.tiff')

    def test_tilestache_big_ben(self):
        # square around Big Ben
        skirt = 300 # metres
        centre = self.big_ben_os

        envelope_srs = SpatialReference()
        envelope_srs.ImportFromEPSG(27700) # British national grid
        envelope = core.Envelope(
                centre[0]-0.5*skirt, centre[0]+0.5*skirt, centre[1]+0.5*skirt, centre[1]-0.5*skirt,
                envelope_srs)

        node = raster.TileStacheSource(config=self.config)
        size = (512, 512)
        tile = node.outputs.osm(envelope=envelope, size=size)
        self.assertIsNotNone(tile)
        self.assertIsInstance(tile, raster.Raster)
        self.assertEqual(tile.array.shape[1], size[0])
        self.assertEqual(tile.array.shape[0], size[1])

        ds = tile.as_dataset()
        self.assertEqual(ds.RasterXSize, size[0])
        self.assertEqual(ds.RasterYSize, size[1])
        tile.write_tiff('big-ben.tiff')

    def test_tilestache_big_ben_small(self):
        # square around Big Ben
        skirt = 100 # metres
        centre = self.big_ben_os

        envelope_srs = SpatialReference()
        envelope_srs.ImportFromEPSG(27700) # British national grid
        envelope = core.Envelope(
                centre[0]-0.5*skirt, centre[0]+0.5*skirt, centre[1]+0.5*skirt, centre[1]-0.5*skirt,
                envelope_srs)

        node = raster.TileStacheSource(config=self.config)
        size = (512, 512)
        tile = node.outputs.osm(envelope=envelope, size=size)
        self.assertIsNotNone(tile)
        self.assertIsInstance(tile, raster.Raster)
        self.assertEqual(tile.array.shape[1], size[0])
        self.assertEqual(tile.array.shape[0], size[1])

        ds = tile.as_dataset()
        self.assertEqual(ds.RasterXSize, size[0])
        self.assertEqual(ds.RasterYSize, size[1])
        tile.write_tiff('big-ben-sm.tiff')

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

        node = raster.TileStacheSource(config=self.config)
        tile = node.outputs.osm(envelope=envelope)
        self.assertIsNotNone(tile)
        self.assertIsInstance(tile, raster.Raster)
        self.assertEqual(tile.array.shape[1], skirt[0])
        self.assertEqual(tile.array.shape[0], skirt[1])

        ds = tile.as_dataset()
        self.assertEqual(ds.RasterXSize, skirt[0])
        self.assertEqual(ds.RasterYSize, skirt[1])
        tile.write_tiff('big-ben-metres.tiff')

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

        e = graph.OutputPad(raster.Raster, self, 'foo', lambda: None)
        e.damaged.connect(damage_cb)

        self.assertEqual(len(damages), 0)
        env1 = core.Envelope(0,0,1,1,self.bng_srs)
        self.assertIsNotNone(env1)
        env2 = core.Envelope(0,0,2,2,self.bng_srs)
        self.assertIsNotNone(env2)

        e.damaged(env1)
        self.assertEqual(len(damages), 1)
        self.assertEqual(damages[-1], env1)
        self.assertNotEqual(damages[-1], env2)

        e.damaged(env2)
        self.assertEqual(len(damages), 2)
        self.assertEqual(damages[-1], env2)
        self.assertNotEqual(damages[-1], env1)

        e.damaged.disconnect(damage_cb)
        e.damaged(env1)
        self.assertEqual(len(damages), 2)
        self.assertEqual(damages[-1], env2)
        self.assertNotEqual(damages[-1], env1)

class TestTransform(unittest.TestCase):
    def setUp(self):
        bng_srs = SpatialReference()
        bng_srs.ImportFromEPSG(27700)
        self.bng_env = core.Envelope(
                500000, 600000, 400000, 300000,
                bng_srs)

        lnglat_srs = SpatialReference()
        lnglat_srs.ImportFromEPSG(4326)
        self.lnglat_env = core.Envelope(
                -2.0, 2.0, 50.0, 54.0,
                lnglat_srs)

    def test_compute_warp(self):
        ll_x, ll_y = raster.compute_warp(
                self.bng_env, (256, 256),
                self.lnglat_env.spatial_reference)
        self.assertTrue(np.all(ll_x > -2))
        self.assertTrue(np.all(ll_x < 2))
        self.assertTrue(np.all(ll_y > 50))
        self.assertTrue(np.all(ll_x < 54))

    def test_proj_to_pixels(self):
        x = np.array([[-1.4, 0.1], [-2, 2], [-3, 8]])
        y = np.array([[50.2, 50.4], [54, 50], [59, 49]])
        px, py = raster.proj_to_pixels(x, y, self.lnglat_env, (128, 64))

        self.assertGreaterEqual(px[0,0], 0)
        self.assertLessEqual(px[0,0], 128)
        self.assertGreaterEqual(px[0,0], 0)
        self.assertLessEqual(px[0,1], 128)
        self.assertGreaterEqual(px[1,1], 0)
        self.assertLessEqual(px[1,1], 128)
        self.assertGreaterEqual(px[1,1], 0)
        self.assertLessEqual(px[1,1], 128)

        self.assertGreaterEqual(py[0,0], 0)
        self.assertLessEqual(py[0,0], 64)
        self.assertGreaterEqual(py[0,0], 0)
        self.assertLessEqual(py[0,1], 64)
        self.assertGreaterEqual(py[1,1], 0)
        self.assertLessEqual(py[1,1], 64)
        self.assertGreaterEqual(py[1,1], 0)
        self.assertLessEqual(py[1,1], 64)

        self.assertLess(px[2,0], 0)
        self.assertGreater(px[2,1], 128)
        self.assertGreater(py[2,0], 64)
        self.assertLess(py[2,1], 0)

        ll_x, ll_y = raster.compute_warp(
                self.bng_env, (256, 256),
                self.lnglat_env.spatial_reference)
        self.assertTrue(np.all(ll_x > -2))
        self.assertTrue(np.all(ll_x < 2))
        self.assertTrue(np.all(ll_y > 50))
        self.assertTrue(np.all(ll_x < 54))

    def test_sample_raster(self):
        src_data = np.atleast_3d(np.array([[1,2,3,4], [5,6,7,8], [9,10,11,12]]))
        src_data = np.dstack((src_data, 2*src_data))
        src = raster.Raster(src_data, self.bng_env)
        src_x = np.array([
            [-1.2, -0.2, 0.8, 1.8, 2.8, 3.2, 4.2],
            [-1.3, -0.3, 0.7, 1.7, 2.7, 3.2, 4.2],
            [-1.2, -0.2, 0.8, 1.8, 2.8, 3.2, 4.2],
            [-1.3, -0.3, 0.7, 1.7, 2.7, 3.2, 4.2],
        ])
        src_y = np.array([
            [-1.2, -0.2, 0.8, 1.8, 2.8, 3.2, 4.2],
            [-1.3, -0.3, 0.7, 1.7, 2.7, 3.2, 4.2],
            [0, 1, 2, 2, 2.3, 1.2, 0.2],
            [0, 1, 2, 2, 2.3, 1.2, 0.2],
        ])
        dst = raster.sample_raster(src_x, src_y, src)

        self.assertEqual(dst.shape[:2], src_x.shape[:2])
        self.assertEqual(dst.shape[2], src_data.shape[2])
        self.assertFalse(np.any(np.isnan(dst)))
        self.assertTrue(np.all(np.isfinite(dst)))
        self.assertTrue(np.all(np.abs(2*dst[:,:,0] - dst[:,:,1]) < 1e-4))
        self.assertIsNot(np.ma.getmask(dst), np.ma.nomask)
        self.assertTrue(np.any(np.ma.getmask(dst)))
        self.assertTrue(np.any(np.logical_not(np.ma.getmask(dst))))

    def test_reproject_raster(self):
        src_data = np.atleast_3d(np.array([[1,2,3,4], [5,6,7,8], [9,10,11,12]]))
        src_data = np.dstack((src_data, 2*src_data))
        src = raster.Raster(src_data, self.bng_env)

        dst = raster.Raster(np.ones((10,5)), self.lnglat_env)
        raster.reproject_raster(dst, src)

class TestRasterBasicNodes(unittest.TestCase):
    def setUp(self):
        self.bng_srs = SpatialReference()
        self.bng_srs.ImportFromEPSG(27700) # British national grid

    def test_placeholder(self):
        ph = raster.PlaceholderRasterSource()
        self.assertIsNotNone(ph.outputs.output)
        rv = ph.outputs.output(
                envelope=core.Envelope(0, 700000, 1300000, 0, self.bng_srs),
                size=(350, 480))
        self.assertIsNotNone(rv)
        rv.write_tiff('placeholder.tiff')

class TestNetwork(unittest.TestCase):
    def setUp(self):
        self.io_loop = IOLoop.instance()
        self.pipeline = network.Pipeline(io_loop=self.io_loop, context=zmq.Context())

        # Add a timeout to terminate the IOLoop if the test takes too long
        def timeout():
            logging.warning('Test took too long. Terminating the event loop.')
            self.io_loop.stop()
        self.io_loop.add_timeout(datetime.timedelta(seconds=5), timeout)

    def test_setup_teardown(self):
        self.io_loop.add_callback(self.io_loop.stop)
        self.io_loop.start()

    def test_create_node(self):
        self.io_loop = IOLoop.instance()

        def node_created(node_uuid):
            logging.info('Node %s created.' % (node_uuid,))
            self.io_loop.stop()
        self.pipeline.node_created.connect(node_created)

        def create_node():
            self.pipeline.create_node('foldbeam.raster', 'PlaceholderRasterSource')

        self.io_loop.add_callback(create_node)
        self.io_loop.start()

    def test_load_configuration(self):
        def pipeline_created():
            logging.info('Pipeline created.')
            self.io_loop.stop()

        def node_created(node_uuid):
            logging.info('Node %s created.' % (node_uuid,))
            self.io_loop.stop()
        self.pipeline.node_created.connect(node_created)

        def create_pipeline():
            logging.info('Creating pipeline')

            nodes = {
                'source': {
                    'type': "foldbeam.raster:PlaceholderRasterSource"
                },
                'sink': {
                    'type': "foldbeam.tilestache:TileStacheServerNode"
                },
            }

            edges = { }
            self.pipeline.load_configuration(nodes, edges, pipeline_created)

        self.io_loop.add_callback(create_pipeline)
        self.io_loop.start()

    def tearDown(self):
        self.pipeline.close()
        del self.pipeline
        del self.io_loop

def test_suite():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(logging.Formatter(fmt='%(name)s:%(levelname)s: %(message)s'))
    logger.addHandler(handler)

    return unittest.TestSuite([
        unittest.makeSuite(TestUtility),
        unittest.makeSuite(TestTileStacheRasterNode),
        unittest.makeSuite(TestBoundary),
        unittest.makeSuite(TestOutputPad),
        unittest.makeSuite(TestTransform),
        unittest.makeSuite(TestRasterBasicNodes),
        unittest.makeSuite(TestNetwork),
    ])
