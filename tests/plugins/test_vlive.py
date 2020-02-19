import unittest  # noqa: F401

import pytest

from streamlink.plugins.vlive import Vlive


class TestPluginVlive:
    valid_urls = [
        ("https://www.vlive.tv/video/156824",),
    ]
    invalid_urls = [
        ("https://www.vlive.tv/events/2019vheartbeat?lang=en",),
        ("https://twitch.tv/",)
    ]

    @pytest.mark.parametrize(["url"], valid_urls)
    def test_can_handle_url(self, url):
        assert Vlive.can_handle_url(url), "url should be handled"

    @pytest.mark.parametrize(["url"], invalid_urls)
    def test_can_handle_url_negative(self, url):
        assert not Vlive.can_handle_url(url), "url should not be handled"
