from streamlink.plugins.rtpa import RTPA
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlRTPA(PluginCanHandleUrl):
    __plugin__ = RTPA

    should_match = [
        "https://www.rtpa.es/tpa-television",
        "https://www.rtpa.es/video:Ciencia%20en%2060%20segundos_551644582052.html",
    ]
