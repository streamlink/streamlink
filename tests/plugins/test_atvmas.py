import unittest

import pytest

from streamlink.plugins.atvmas import atvmas


class TestPluginatvmas:
    valid_urls = [
        ("http://www.atvmas.pe/envivo",),
    ]
    invalid_urls = [
        ("https://news.now.com/home/local",),
        ("http://www.atv.pe/envivo",),
        ("https://www.youtube.com",)
    ]

    @pytest.mark.parametrize(["url"], valid_urls)
    def test_can_handle_url(self, url):
        assert atvmas.can_handle_url(url), "url should be handled"

    @pytest.mark.parametrize(["url"], invalid_urls)
    def test_can_handle_url_negative(self, url):
        assert not atvmas.can_handle_url(url), "url should not be handled"

    def test_transform(self):
        assert atvmas.transform_token(u'6b425761cc8a86569b1a05a9bf1870c95fca717dOK', 436171) == "6b425761cc8a86569b1a05a9bf1870c95fca717d"
