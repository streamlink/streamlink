from streamlink.plugins.teleclubzoom import TeleclubZoom
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlTeleclubZoom(PluginCanHandleUrl):
    __plugin__ = TeleclubZoom

    should_match = [
        'https://www.teleclubzoom.ch',
        'https://www.teleclubzoom.ch/',
    ]
