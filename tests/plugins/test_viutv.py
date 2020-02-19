import unittest  # noqa: F401

import pytest

from streamlink.plugins.viutv import ViuTV


class TestPluginViuTV:
    valid_urls = [
        ("https://viu.tv/ch/99",),
    ]
    invalid_urls = [
        ("https://viu.tv/encore/king-maker-ii/king-maker-iie4fuk-hei-baan-hui-ji-on-ji-sun-dang-cheung",),
        ("https://www.youtube.com",)
    ]

    @pytest.mark.parametrize(["url"], valid_urls)
    def test_can_handle_url(self, url):
        assert ViuTV.can_handle_url(url), "url should be handled"

    @pytest.mark.parametrize(["url"], invalid_urls)
    def test_can_handle_url_negative(self, url):
        assert not ViuTV.can_handle_url(url), "url should not be handled"
