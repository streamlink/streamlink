from streamlink.plugins.liveedu import LiveEdu
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlLiveEdu(PluginCanHandleUrl):
    __plugin__ = LiveEdu

    should_match = [
        'https://www.liveedu.tv/',
    ]
