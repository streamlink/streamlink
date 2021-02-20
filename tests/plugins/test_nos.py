from streamlink.plugins.nos import NOS
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlNOS(PluginCanHandleUrl):
    __plugin__ = NOS

    should_match = [
        'https://nos.nl/livestream/2220100-wk-sprint-schaatsen-1-000-meter-mannen.html',
    ]
