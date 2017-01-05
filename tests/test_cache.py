import sys
import unittest
import tempfile
import os.path

import streamlink.cache
from shutil import rmtree

try:
    from unittest.mock import patch
except ImportError:
    from mock import patch
is_py2 = (sys.version_info[0] == 2)


class TestCache(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp("streamlink-test")

        streamlink.cache.cache_dir = self.tmp_dir
        self.cache = streamlink.cache.Cache("cache.json")

    def tearDown(self):
        rmtree(self.tmp_dir)

    def test_get_no_file(self):
        self.assertEqual(self.cache.get("missing-value"), None)
        self.assertEqual(self.cache.get("missing-value", default="default"), "default")

    def test_put_get(self):
        self.cache.set("value", 1)
        self.assertEqual(self.cache.get("value"), 1)

    def test_put_get_prefix(self):
        self.cache.key_prefix = "test"
        self.cache.set("value", 1)
        self.assertEqual(self.cache.get("value"), 1)

    def test_key_prefix(self):
        self.cache.key_prefix = "test"
        self.cache.set("value", 1)
        self.assertTrue("test:value" in self.cache._cache)
        self.assertEqual(1, self.cache._cache["test:value"]["value"])

    @patch('os.path.exists', return_value=True)
    def test_load_fail(self, exists_mock):
        if is_py2:
            patch('__builtin__.open', side_effect=IOError)
        else:
            patch('streamlink.cache.open', side_effect=IOError)
        self.cache._load()
        self.assertEqual({}, self.cache._cache)

    def test_expired(self):
        self.cache.set("value", 10, expires=-1)
        self.assertEqual(None, self.cache.get("value"))

    def test_create_directory(self):
        try:
            streamlink.cache.cache_dir = os.path.join(tempfile.gettempdir(), "streamlink-test")
            cache = streamlink.cache.Cache("cache.json")
            self.assertFalse(os.path.exists(cache.filename))
            cache.set("value", 10)
            self.assertTrue(os.path.exists(cache.filename))
        finally:
            rmtree(streamlink.cache.cache_dir, ignore_errors=True)

    @patch('os.makedirs', side_effect=OSError)
    def test_create_directory_fail(self, makedirs):
        try:
            streamlink.cache.cache_dir = os.path.join(tempfile.gettempdir(), "streamlink-test")
            cache = streamlink.cache.Cache("cache.json")
            self.assertFalse(os.path.exists(cache.filename))
            cache.set("value", 10)
            self.assertFalse(os.path.exists(cache.filename))
        finally:
            rmtree(streamlink.cache.cache_dir, ignore_errors=True)
