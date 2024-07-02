from streamlink.plugins.douyin import Douyin
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlDouyin(PluginCanHandleUrl):
    __plugin__ = Douyin

    should_match_groups = [
        ("https://live.douyin.com/ROOM_ID", {"room_id": "ROOM_ID"}),
    ]

    should_not_match = [
        "https://live.douyin.com",
    ]
