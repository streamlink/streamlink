from streamlink.plugins.qq import QQ
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlQQ(PluginCanHandleUrl):
    __plugin__ = QQ

    should_match = [
        "http://live.qq.com/10003715",
        "http://live.qq.com/10007266",
        "http://live.qq.com/10039165",
        "http://m.live.qq.com/10003715",
        "http://m.live.qq.com/10007266",
        "http://m.live.qq.com/10039165"
    ]

    should_match_groups = [
        ("http://live.qq.com/10003715", {
            "room_id": "10003715"
        }),
        ("http://m.live.qq.com/10039165", {
            "room_id": "10039165"
        }),
    ]

    should_not_match = [
        "http://live.qq.com/",
        "http://qq.com/",
        "http://www.qq.com/"
    ]
