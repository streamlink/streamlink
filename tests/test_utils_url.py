import unittest

from streamlink.utils.url import (
    update_scheme, url_equal, url_concat, update_qsd
)


class TestUtilURL(unittest.TestCase):
    def test_update_scheme(self):
        self.assertEqual(
            "https://example.com/foo",  # becomes https
            update_scheme("https://other.com/bar", "//example.com/foo")
        )
        self.assertEqual(
            "http://example.com/foo",  # becomes http
            update_scheme("http://other.com/bar", "//example.com/foo")
        )
        self.assertEqual(
            "http://example.com/foo",  # remains unchanged
            update_scheme("https://other.com/bar", "http://example.com/foo")
        )
        self.assertEqual(
            "https://example.com/foo",  # becomes https
            update_scheme("https://other.com/bar", "example.com/foo")
        )

    def test_url_equal(self):
        self.assertTrue(url_equal("http://test.com/test", "http://test.com/test"))
        self.assertFalse(url_equal("http://test.com/test", "http://test.com/test2"))

        self.assertTrue(url_equal("http://test.com/test", "http://test.com/test2", ignore_path=True))
        self.assertTrue(url_equal("http://test.com/test", "https://test.com/test", ignore_scheme=True))
        self.assertFalse(url_equal("http://test.com/test", "https://test.com/test"))

        self.assertTrue(url_equal("http://test.com/test", "http://test.com/test#hello", ignore_fragment=True))
        self.assertTrue(url_equal("http://test.com/test", "http://test2.com/test", ignore_netloc=True))
        self.assertFalse(url_equal("http://test.com/test", "http://test2.com/test1", ignore_netloc=True))

    def test_url_concat(self):
        self.assertEqual(url_concat("http://test.se", "one", "two", "three"), "http://test.se/one/two/three")
        self.assertEqual(url_concat("http://test.se", "/one", "/two", "/three"), "http://test.se/one/two/three")
        self.assertEqual(url_concat("http://test.se/one", "../two", "three"), "http://test.se/two/three")
        self.assertEqual(url_concat("http://test.se/one", "../two", "../three"), "http://test.se/three")

    def test_update_qsd(self):
        self.assertEqual(update_qsd("http://test.se?one=1&two=3", {"two": 2}), "http://test.se?one=1&two=2")
        self.assertEqual(update_qsd("http://test.se?one=1&two=3", remove=["two"]), "http://test.se?one=1")
        self.assertEqual(update_qsd("http://test.se?one=1&two=3", {"one": None}, remove="*"), "http://test.se?one=1")
