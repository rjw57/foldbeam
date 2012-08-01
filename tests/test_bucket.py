import os
import tempfile
import shutil
import unittest

from foldbeam.bucket import Bucket, BadFileNameError, Layer

data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))

class BaseTestBucket(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmp_dir = tempfile.mkdtemp(prefix='test_bucket')
        self.bucket = Bucket(self.tmp_dir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir)

class TestCore(BaseTestBucket):
    def test_empty_bucket(self):
        self.assertEqual(len(self.bucket.layers), 0)
        self.assertIsNone(self.bucket.primary_file_name)

    def test_bad_file_name(self):
        this_file = open(__file__)
        self.assertRaises(BadFileNameError, lambda: self.bucket.add('../bad_filename', this_file))

class TestShapeFile(BaseTestBucket):
    def test_simple_upload_bucket(self):
        shp_file_path = os.path.join(data_dir, 'ne_110m_admin_0_countries.shp')
        self.assertTrue(os.path.exists(shp_file_path))
        shp_file = open(shp_file_path)

        shx_file_path = os.path.join(data_dir, 'ne_110m_admin_0_countries.shx')
        self.assertTrue(os.path.exists(shx_file_path))
        shx_file = open(shx_file_path)

        prj_file_path = os.path.join(data_dir, 'ne_110m_admin_0_countries.prj')
        self.assertTrue(os.path.exists(prj_file_path))
        prj_file = open(prj_file_path)

        self.assertEqual(len(self.bucket.layers), 0)
        self.assertIsNone(self.bucket.primary_file_name)
        self.bucket.add('foo.shp', shp_file)
        self.assertIsNotNone(self.bucket.primary_file_name)
        self.assertEqual(self.bucket.primary_file_name, 'foo.shp')
        self.assertEqual(len(self.bucket.layers), 0)

        self.bucket.add('foo.shx', shx_file)
        self.assertEqual(self.bucket.primary_file_name, 'foo.shp')
        self.assertEqual(len(self.bucket.layers), 1)
        self.assertEqual(self.bucket.layers[0].name, 'foo')
        self.assertIsNone(self.bucket.layers[0].spatial_reference)

        self.bucket.add('foo.prj', prj_file)
        self.assertEqual(self.bucket.primary_file_name, 'foo.shp')
        self.assertEqual(len(self.bucket.layers), 1)
        self.assertEqual(self.bucket.layers[0].name, 'foo')
        self.assertIsNotNone(self.bucket.layers[0].spatial_reference)

        l = self.bucket.layers[0]
        self.assertEqual(l.type, Layer.VECTOR_TYPE)
        self.assertEqual(l.name, 'foo')

        self.assertIsNotNone(l.mapnik_datasource)

        # check datasource loaded OK
        env = l.mapnik_datasource.envelope()

        self.assertAlmostEqual(env.minx, -180)
        self.assertAlmostEqual(env.miny, -90)
        self.assertAlmostEqual(env.maxx, 180)
        self.assertAlmostEqual(env.maxy, 83.64513)

class TestGeoTiff(BaseTestBucket):
    def test_upload(self):
        raster_file_path = os.path.join(data_dir, 'spain.tiff')
        self.assertTrue(os.path.exists(raster_file_path))
        raster_file = open(raster_file_path)

        self.assertEqual(len(self.bucket.layers), 0)
        self.assertIsNone(self.bucket.primary_file_name)
        self.bucket.add('spain.tiff', raster_file)
        self.assertIsNotNone(self.bucket.primary_file_name)
        self.assertEqual(self.bucket.primary_file_name, 'spain.tiff')
        self.assertEqual(len(self.bucket.layers), 1)
        self.assertIsNotNone(self.bucket.layers[0].spatial_reference)

        l = self.bucket.layers[0]
        self.assertEqual(l.type, Layer.RASTER_TYPE)
        self.assertEqual(l.name, 'spain.tiff')

        self.assertIsNotNone(l.mapnik_datasource)

        # check datasource loaded OK
        env = l.mapnik_datasource.envelope()

        self.assertAlmostEqual(env.minx, -14637)
        self.assertAlmostEqual(env.miny, 3903178)
        self.assertAlmostEqual(env.maxx, 1126863)
        self.assertAlmostEqual(env.maxy, 4859678)

class TestPNG(BaseTestBucket):
    def test_upload(self):
        raster_file_path = os.path.join(data_dir, 'spain.png')
        self.assertTrue(os.path.exists(raster_file_path))
        raster_file = open(raster_file_path)

        aux_raster_file_path = os.path.join(data_dir, 'spain.png.aux.xml')
        self.assertTrue(os.path.exists(aux_raster_file_path))
        aux_raster_file = open(aux_raster_file_path)

        self.assertEqual(len(self.bucket.layers), 0)
        self.assertIsNone(self.bucket.primary_file_name)
        self.bucket.add('spain.png', raster_file)
        self.assertIsNotNone(self.bucket.primary_file_name)
        self.assertEqual(self.bucket.primary_file_name, 'spain.png')
        self.assertEqual(len(self.bucket.layers), 1)
        self.assertIsNone(self.bucket.layers[0].spatial_reference)

        self.bucket.add('spain.png.aux.xml', aux_raster_file)
        self.assertIsNotNone(self.bucket.layers[0].spatial_reference)

        l = self.bucket.layers[0]
        self.assertEqual(l.type, Layer.RASTER_TYPE)
        self.assertEqual(l.name, 'spain.png')

        self.assertIsNotNone(l.mapnik_datasource)

        # check datasource loaded OK
        env = l.mapnik_datasource.envelope()

        self.assertAlmostEqual(env.minx, -14637)
        self.assertAlmostEqual(env.miny, 3903178)
        self.assertAlmostEqual(env.maxx, 1126863)
        self.assertAlmostEqual(env.maxy, 4859678)
