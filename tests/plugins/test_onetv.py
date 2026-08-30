from streamlink.plugins.onetv import OneTV
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlOneTV(PluginCanHandleUrl):
    __plugin__ = OneTV

    should_match = [
        "https://www.1tv.ru/live",
        "http://www.1tv.ru/live",
        "https://static.1tv.ru/eump/embeds/1tv_live_orbit-plus-4.html?muted=no",
        "https://static.1tv.ru/eump/pages/1tv_live.html",
        "https://static.1tv.ru/eump/pages/1tv_live_orbit-plus-4.html",
    ]

    should_not_match = [
        "http://www.1tv.ru/some-show/some-programme-2018-03-10",
        "https://www.ctc.ru/online",
        "http://www.ctc.ru/online",
        "https://www.chetv.ru/online",
        "http://www.chetv.ru/online",
        "https://www.ctclove.ru/online",
        "http://www.ctclove.ru/online",
        "https://www.domashny.ru/online",
        "http://www.domashny.ru/online",
    ]
