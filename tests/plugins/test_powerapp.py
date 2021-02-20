from streamlink.plugins.powerapp import PowerApp
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlPowerApp(PluginCanHandleUrl):
    __plugin__ = PowerApp

    should_match = [
        'http://powerapp.com.tr/tv/powertv4k',
        'http://powerapp.com.tr/tv/powerturktv4k',
        'http://powerapp.com.tr/tv/powerEarthTV',
        'http://www.powerapp.com.tr/tvs/powertv'
    ]

    should_not_match = [
        'http://powerapp.com.tr/',
    ]
