from unittest.mock import Mock

from freezegun import freeze_time

from streamlink.plugins.vinhlongtv import VinhLongTV
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlVinhLongTV(PluginCanHandleUrl):
    __plugin__ = VinhLongTV

    should_match = [
        "https://www.thvli.vn/live/thvl1-hd",
        "https://www.thvli.vn/live/thvl2-hd",
        "https://www.thvli.vn/live/thvl3-hd",
        "https://www.thvli.vn/live/thvl4-hd",
    ]


@freeze_time("2022-09-25T00:04:45Z")
def test_headers():
    # noinspection PyUnresolvedReferences
    assert VinhLongTV(Mock(), "")._get_headers() == {
        "X-SFD-Date": "20220925000445",
        "X-SFD-Key": "3507c190ae8befda3bfa8e2c00af3c7a",
    }
