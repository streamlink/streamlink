from streamlink.plugins.attheshore import AtTheShore
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlAtTheShore(PluginCanHandleUrl):
    __plugin__ = AtTheShore

    should_match = [
        "http://attheshore.com/livecam-steelpier564",
    ]

    should_not_match = [
        "http://attheshore.com/livecams",
    ]
