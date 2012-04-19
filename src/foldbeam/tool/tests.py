import unittest
import render

class TestRender(unittest.TestCase):
    def test_wgs84_latlng(self):
        render.main(
            '--aerial --epsg 4326 -l -180 -r 180 -t 90 -b -90 -o render-test-1.tiff --cache-dir tilestache -w 512'.split(' ')
        )

def test_suite():
    return unittest.TestSuite([
        unittest.makeSuite(TestRender),
    ])
