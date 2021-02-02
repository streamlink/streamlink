from streamlink.plugins.tv360 import TV360
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlTV360(PluginCanHandleUrl):
    __plugin__ = TV360

    should_match = [
        'http://tv360.com.tr/canli-yayin',
    ]
