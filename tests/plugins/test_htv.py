from streamlink.plugins.htv import HTV
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlHTV(PluginCanHandleUrl):
    __plugin__ = HTV

    should_match_groups = [
        ("https://htv.com.vn/truc-tuyen", {}),
        ("https://htv.com.vn/truc-tuyen?channel=123", {"channel": "123"}),
        ("https://htv.com.vn/truc-tuyen?channel=123&foo", {"channel": "123"}),
        ("https://www.htv.com.vn/truc-tuyen", {}),
        ("https://www.htv.com.vn/truc-tuyen?channel=123", {"channel": "123"}),
        ("https://www.htv.com.vn/truc-tuyen?channel=123&foo", {"channel": "123"}),
    ]

    should_not_match = [
        "https://htv.com.vn/",
        "https://htv.com.vn/any/path",
        "https://htv.com.vn/truc-tuyen?foo",
        "https://www.htv.com.vn/",
        "https://www.htv.com.vn/any/path",
        "https://www.htv.com.vn/truc-tuyen?foo",
    ]
