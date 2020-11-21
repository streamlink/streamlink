import unittest  # noqa: F401

import pytest

from streamlink.plugins.nownews import NowNews


class TestPluginNowNews:
    valid_urls = [
        ("https://news.now.com/home/live",),
        ("http://news.now.com/home/live",),
        ("https://news.now.com/home/live331a",),
        ("http://news.now.com/home/live331a",)
    ]
    invalid_urls = [
        ("https://news.now.com/home/local",),
        ("http://media.now.com.hk/",),
        ("https://www.youtube.com",)
    ]

    @pytest.mark.parametrize(["url"], valid_urls)
    def test_can_handle_url(self, url):
        assert NowNews.can_handle_url(url), "url should be handled"

    @pytest.mark.parametrize(["url"], invalid_urls)
    def test_can_handle_url_negative(self, url):
        assert not NowNews.can_handle_url(url), "url should not be handled"
