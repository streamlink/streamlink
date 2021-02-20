from streamlink.plugins.ozolio import Ozolio
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlOzolio(PluginCanHandleUrl):
    __plugin__ = Ozolio

    should_match = [
        "http://ozolio.com/explore/",
        "https://www.ozolio.com/explore/WLWJ00000021",
    ]

    should_not_match = [
        "http://relay.ozolio.com/pub.api?cmd=avatar&oid=CID_XNQT0000099E",
    ]
