from streamlink.plugins.tv8 import TV8
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlTV8(PluginCanHandleUrl):
    __plugin__ = TV8

    should_match = [
        'https://www.tv8.com.tr/canli-yayin',
    ]
