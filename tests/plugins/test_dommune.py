from streamlink.plugins.dommune import Dommune
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlDommune(PluginCanHandleUrl):
    __plugin__ = Dommune

    should_match = [
        'http://dommune.com',
    ]
