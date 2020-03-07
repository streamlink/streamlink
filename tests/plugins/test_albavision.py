import unittest  # noqa: F401

import pytest

from streamlink.plugins.albavision import Albavision


class TestPluginAlbavision:
    valid_urls = [
        ("https://www.elnueve.com.ar/en-vivo",),
        ("http://www.rts.com.ec/envivo",),
        ("https://www.tvc.com.ec/envivo",),
        ("http://www.atv.pe/envivo/ATV",),
        ("http://www.atv.pe/envivo/ATVMas",),
    ]
    invalid_urls = [
        ("https://news.now.com/home/local",),
        ("http://media.now.com.hk/",),
        ("https://www.youtube.com",)
    ]

    @pytest.mark.parametrize(["url"], valid_urls)
    def test_can_handle_url(self, url):
        assert Albavision.can_handle_url(url), "url should be handled"

    @pytest.mark.parametrize(["url"], invalid_urls)
    def test_can_handle_url_negative(self, url):
        assert not Albavision.can_handle_url(url), "url should not be handled"

    def test_transform(self):
        token = Albavision.transform_token(u'6b425761cc8a86569b1a05a9bf1870c95fca717dOK', 436171)
        assert token == "6b425761cc8a86569b1a05a9bf1870c95fca717d"
