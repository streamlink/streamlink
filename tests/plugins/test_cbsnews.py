import unittest  # noqa: F401

import pytest

from streamlink.plugins.cbsnews import CBSNews


class TestCBSNews:
    valid_urls = [
        ("https://www.cbsnews.com/live/cbs-sports-hq/",),
        ("https://www.cbsnews.com/live/cbsn-local-bay-area/",),
        ("https://www.cbsnews.com/live/",),
    ]
    invalid_urls = [
        ("https://www.cbsnews.com/feature/election-2020/",),
        ("https://www.cbsnews.com/48-hours/",),
        ("https://twitch.tv/",)
    ]

    @pytest.mark.parametrize(["url"], valid_urls)
    def test_can_handle_url(self, url):
        assert CBSNews.can_handle_url(url), "url should be handled"

    @pytest.mark.parametrize(["url"], invalid_urls)
    def test_can_handle_url_negative(self, url):
        assert not CBSNews.can_handle_url(url), "url should not be handled"
