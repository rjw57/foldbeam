from _support import *
import logging
import os
import pyopencl
import sys
import unittest

class TestSupport(unittest.TestCase):
    def setUp(self):
        self.context = pyopencl.create_some_context()
        os.environ['PYOPENCL_COMPILER_OUTPUT'] = '1'

    def test_kernel_dir(self):
        self.assertIsInstance(kernel_dir(), basestring)

    def test_kernel_filename(self):
        filename = kernel_filename('merc')
        self.assertTrue(filename.endswith('merc.cl'))
        self.assertTrue(os.path.isfile(filename))

    def test_kernel_program(self):
        if self.context is None:
            return
        program = kernel_program(self.context, 'merc')
        self.assertIsNotNone(program)

def test_suite():
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    return unittest.TestSuite([
        unittest.makeSuite(TestSupport),
    ])
