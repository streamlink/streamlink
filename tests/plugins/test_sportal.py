from streamlink.plugins.sportal import Sportal
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlSportal(PluginCanHandleUrl):
    __plugin__ = Sportal

    should_match = [
        "http://sportal.bg/sportal_live_tv.php?str=15",
        "http://www.sportal.bg/sportal_live_tv.php?",
        "http://www.sportal.bg/sportal_live_tv.php?str=15",
    ]
