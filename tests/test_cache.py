import datetime
import os.path
import tempfile
import unittest
from shutil import rmtree
from unittest.mock import patch

import streamlink.cache


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
        patch('streamlink.cache.open', side_effect=IOError)
        self.cache._load()
        self.assertEqual({}, self.cache._cache)

    def test_expired(self):
        self.cache.set("value", 10, expires=-20)
        self.assertEqual(None, self.cache.get("value"))

    def test_expired_at_before(self):
        self.cache.set("value", 10, expires_at=datetime.datetime.now() - datetime.timedelta(seconds=20))
        self.assertEqual(None, self.cache.get("value"))

    def test_expired_at_after(self):
        self.cache.set("value", 10, expires_at=datetime.datetime.now() + datetime.timedelta(seconds=20))
        self.assertEqual(10, self.cache.get("value"))

    @patch("streamlink.cache.mktime", side_effect=OverflowError)
    def test_expired_at_raise_overflowerror(self, mock):
        self.cache.set("value", 10, expires_at=datetime.datetime.now())
        self.assertEqual(None, self.cache.get("value"))

    def test_not_expired(self):
        self.cache.set("value", 10, expires=20)
        self.assertEqual(10, self.cache.get("value"))

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

    def test_get_all(self):
        self.cache.set("test1", 1)
        self.cache.set("test2", 2)

        self.assertDictEqual(
            {"test1": 1, "test2": 2},
            self.cache.get_all())

    def test_get_all_prefix(self):
        self.cache.set("test1", 1)
        self.cache.set("test2", 2)
        self.cache.key_prefix = "test"
        self.cache.set("test3", 3)
        self.cache.set("test4", 4)

        self.assertDictEqual(
            {"test3": 3, "test4": 4},
            self.cache.get_all())

    def test_get_all_prune(self):
        self.cache.set("test1", 1)
        self.cache.set("test2", 2, -1)

        self.assertDictEqual(
            {"test1": 1},
            self.cache.get_all())
