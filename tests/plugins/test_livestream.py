from streamlink.plugins.livestream import Livestream
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlLivestream(PluginCanHandleUrl):
    __plugin__ = Livestream

    should_match = [
        'https://livestream.com/',
        'https://www.livestream.com/',
        'https://livestream.com/accounts/22300508/events/6675945',
    ]
