import unittest

from streamlink.plugins.albavision import Albavision
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlAlbavision(PluginCanHandleUrl):
    __plugin__ = Albavision

    should_match = [
        "https://www.elnueve.com.ar/en-vivo",
        "http://www.rts.com.ec/envivo",
        "https://www.tvc.com.ec/envivo",
        "http://www.atv.pe/envivo/ATV",
        "http://www.atv.pe/envivo/ATVMas",
    ]
    should_not_match = [
        "https://news.now.com/home/local",
        "http://media.now.com.hk/",
    ]


class TestPluginAlbavision(unittest.TestCase):
    def test_transform(self):
        token = Albavision.transform_token("6b425761cc8a86569b1a05a9bf1870c95fca717dOK", 436171)
        assert token == "6b425761cc8a86569b1a05a9bf1870c95fca717d"
