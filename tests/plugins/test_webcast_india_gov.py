from streamlink.plugins.webcast_india_gov import WebcastIndiaGov
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlWebcastIndiaGov(PluginCanHandleUrl):
    __plugin__ = WebcastIndiaGov

    should_match = [
        "http://webcast.gov.in/ddpunjabi/",
        "http://webcast.gov.in/#Channel1",
        "http://webcast.gov.in/#Channel3",
    ]
