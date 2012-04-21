from _support import *
import logging
import math
import numpy as np
import os
import pyopencl
import sys
import timeit
import unittest

class TestSupport(unittest.TestCase):
    def setUp(self):
        self.context = pyopencl.create_some_context()
        self.queue = pyopencl.CommandQueue(self.context)
        os.environ['PYOPENCL_COMPILER_OUTPUT'] = '1'

    def test_kernel_dir(self):
        self.assertIsInstance(kernel_dir(), basestring)

    def test_kernel_filename(self):
        filename = kernel_filename('merc')
        self.assertTrue(filename.endswith('merc.cl'))
        self.assertTrue(os.path.isfile(filename))

    def test_kernel_load_program(self):
        if self.context is None:
            return
        program = kernel_load_program(self.context, 'merc')
        self.assertIsNotNone(program)

    def test_load_projection_kernels(self):
        if self.context is None:
            return
        entries = load_projection_kernels(self.context, 'merc')
        self.assertIsNotNone(entries)
        self.assertEqual(len(entries), 1)
        self.assertIn('merc', entries)

        merc = entries['merc']
        self.assertEqual(merc.name, 'merc')
        self.assertIsNotNone(merc.forward_kernel)
        self.assertEqual(merc.forward_kernel.function_name, 'merc_forward_kernel')
        self.assertEqual(merc.inverse_kernel.function_name, 'merc_inverse_kernel')
        self.assertEqual(len(merc.standard_params), 3)
        self.assertIn('k0', merc.standard_params)
        self.assertIn('e', merc.standard_params)
        self.assertIn('es', merc.standard_params)
        self.assertEqual(len(merc.custom_params), 2)
        self.assertIn('tlat_ts', merc.custom_params)
        self.assertIn('rlat_ts', merc.custom_params)

    def test_project_merc(self):
        if self.context is None:
            return

        merc = load_projection_kernels(self.context, 'merc')['merc']
        params = {
            'k0': np.float32(1.0),
            'es': np.float32(0.006694379990),
            'e': np.float32(np.sqrt(0.006694379990)),
            'tlat_ts': np.int32(0),
            'rlat_ts': np.float32(0.0),
        }
        x1, y1 = np.random.rand(256,256).ravel(), np.random.rand(256,256).ravel()
        def doit():
            x2, y2 = merc(self.queue, x1, y1, **params)
            return x2, y2
        t = timeit.Timer(stmt=doit)
        print "merc forward %.2f usec/pass" % (1000000 * t.timeit(number=10)/10)
        x2, y2 = doit()
        for a, b in zip(x1, x2):
            self.assertAlmostEqual(a, b)
        x1, y1 = np.random.rand(256,256).ravel(), np.random.rand(256,256).ravel()
        def doit():
            x2, y2 = merc(self.queue, x1, y1, inverse=True, **params)
            return x2, y2
        t = timeit.Timer(stmt=doit)
        print "merc inverse %.2f usec/pass" % (1000000 * t.timeit(number=10)/10)
        x2, y2 = doit()

    def test_project_tmerc(self):
        if self.context is None:
            return

        tmerc = load_projection_kernels(self.context, 'tmerc')['tmerc']
        params = {
            'k0': np.float32(1.0),
            'es': np.float32(0.006694379990),
            'e': np.float32(np.sqrt(0.006694379990)),
            'phi0': np.float32((49.0 / 360.0) * math.pi * 2.0),
        }
        x1, y1 = np.random.rand(256,256).ravel(), np.random.rand(256,256).ravel()
        def doit():
            x2, y2 = tmerc(self.queue, x1, y1, **params)
            return x2, y2
        t = timeit.Timer(stmt=doit)
        print "tmerc forward %.2f usec/pass" % (1000000 * t.timeit(number=10)/10)
        x2, y2 = doit()

def test_suite():
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    return unittest.TestSuite([
        unittest.makeSuite(TestSupport),
    ])
