from streamlink.plugins.webtv import WebTV
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlWebTV(PluginCanHandleUrl):
    __plugin__ = WebTV

    should_match = [
        "http://planetmutfak.web.tv",
        "http://telex.web.tv",
        "http://nasamedia.web.tv",
        "http://genctv.web.tv",
        "http://etvmanisa.web.tv",
        "http://startv.web.tv",
        "http://akuntv.web.tv",
        "http://telebarnn.web.tv",
        "http://kanal48.web.tv",
        "http://digi24tv.web.tv",
        "http://french24.web.tv",
    ]
