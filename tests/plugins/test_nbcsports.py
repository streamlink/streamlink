from streamlink.plugins.nbcsports import NBCSports
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlNBCSports(PluginCanHandleUrl):
    __plugin__ = NBCSports

    should_match = [
        'https://www.nbcsports.com/video/evertons-wayne-rooney-completes-hat-trick-goal-midfield',
    ]
