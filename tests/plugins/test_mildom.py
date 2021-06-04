from streamlink.plugins.mildom import Mildom
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlMildom(PluginCanHandleUrl):
    __plugin__ = Mildom

    should_match = [
        'https://www.mildom.com/10707087',
        'https://www.mildom.com/playback/10707087/10707087-c0p1d4d2lrnb79gc0kqg',
    ]

    should_not_match = [
        'https://support.mildom.com',
        'https://www.mildom.com/ranking',
    ]
