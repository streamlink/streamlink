from streamlink.plugins.showroom import Showroom
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlShowroom(PluginCanHandleUrl):
    __plugin__ = Showroom

    should_match = [
        "https://www.showroom-live.com/48_NISHIMURA_NANAKO",
        "https://www.showroom-live.com/room/profile?room_id=61734",
        "http://showroom-live.com/48_YAMAGUCHI_MAHO",
        "https://www.showroom-live.com/4b9581094890",
        "https://www.showroom-live.com/157941217780",
        "https://www.showroom-live.com/madokacom",
    ]
