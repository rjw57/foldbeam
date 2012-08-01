import logging
import os
import shutil
import tempfile
import unittest

from foldbeam.web import model

logging.basicConfig(level=logging.WARNING)
log = logging.getLogger()

class TempDbMixin(object):
    def setUp(self):
        self._old_shelve = model._shelve_loc
        self._old_buckets = model._bucket_loc
        self._tmp_dir = tempfile.mkdtemp(prefix='test_db_')
        model._shelve_loc = os.path.join(self._tmp_dir, 'db')
        model._bucket_loc = os.path.join(self._tmp_dir, 'buckets')

    def tearDown(self):
        model._shelve_loc = self._old_shelve
        model._bucket_loc = self._old_buckets
        shutil.rmtree(self._tmp_dir)
