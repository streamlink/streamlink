from streamlink.plugins.qq import QQ
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlQQ(PluginCanHandleUrl):
    __plugin__ = QQ

    should_match_groups = [
        ("https://live.qq.com/", {}),
        ("https://live.qq.com/123456789", {"room_id": "123456789"}),
        ("https://m.live.qq.com/123456789", {"room_id": "123456789"}),
    ]
