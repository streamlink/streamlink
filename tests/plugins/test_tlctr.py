from streamlink.plugins.tlctr import TLCtr
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlTLCtr(PluginCanHandleUrl):
    __plugin__ = TLCtr

    should_match = [
        'https://www.tlctv.com.tr/canli-izle',
    ]
