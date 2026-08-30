from streamlink.plugins.mixcloud import Mixcloud
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlMixcloud(PluginCanHandleUrl):
    __plugin__ = Mixcloud

    should_match_groups = [
        ("http://mixcloud.com/live/user", {"user": "user"}),
        ("http://www.mixcloud.com/live/user", {"user": "user"}),
        ("https://mixcloud.com/live/user", {"user": "user"}),
        ("https://www.mixcloud.com/live/user", {"user": "user"}),
        ("https://www.mixcloud.com/live/user/anything", {"user": "user"}),
    ]

    should_not_match = [
        "https://www.mixcloud.com/",
        "https://www.mixcloud.com/live",
        "https://www.mixcloud.com/live/",
        "https://www.mixcloud.com/other",
    ]
