import unittest

from streamlink.plugins.tvrby import TVRBy
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlTVRBy(PluginCanHandleUrl):
    __plugin__ = TVRBy

    should_match = [
        "http://www.tvr.by/televidenie/belarus-1/",
        "http://www.tvr.by/televidenie/belarus-1",
        "http://www.tvr.by/televidenie/belarus-24/",
        "http://www.tvr.by/televidenie/belarus-24",
    ]


class TestPluginTVRBy(unittest.TestCase):
    def test_url_fix(self):
        self.assertTrue(
            "http://www.tvr.by/televidenie/belarus-1/",
            TVRBy("http://www.tvr.by/televidenie/belarus-1/").url)
        self.assertTrue(
            "http://www.tvr.by/televidenie/belarus-1/",
            TVRBy("http://www.tvr.by/televidenie/belarus-1").url)
        self.assertTrue(
            "http://www.tvr.by/televidenie/belarus-24/",
            TVRBy("http://www.tvr.by/televidenie/belarus-24/").url)
        self.assertTrue(
            "http://www.tvr.by/televidenie/belarus-24/",
            TVRBy("http://www.tvr.by/televidenie/belarus-24").url)
