from unittest.mock import Mock

import pytest

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


class TestPluginTVRBy:
    @pytest.mark.parametrize(("url", "expected"), [
        (
            "http://www.tvr.by/televidenie/belarus-1/",
            "http://www.tvr.by/televidenie/belarus-1/",
        ),
        (
            "http://www.tvr.by/televidenie/belarus-1",
            "http://www.tvr.by/televidenie/belarus-1/",
        ),
    ])
    def test_url_fix(self, url, expected):
        assert TVRBy(Mock(), url).url == expected
