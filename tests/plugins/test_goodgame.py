from streamlink.plugins.goodgame import GoodGame
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlGoodGame(PluginCanHandleUrl):
    __plugin__ = GoodGame

    should_match_groups = [
        (("default", "https://goodgame.ru/USERNAME"), {"name": "USERNAME"}),
        (("default", "https://goodgame.ru/USERNAME/"), {"name": "USERNAME"}),
        (("default", "https://goodgame.ru/USERNAME?foo=bar"), {"name": "USERNAME"}),
        (("default", "https://www.goodgame.ru/USERNAME"), {"name": "USERNAME"}),
        (("channel", "https://goodgame.ru/channel/CHANNELNAME"), {"channel": "CHANNELNAME"}),
        (("channel", "https://goodgame.ru/channel/CHANNELNAME/"), {"channel": "CHANNELNAME"}),
        (("channel", "https://goodgame.ru/channel/CHANNELNAME?foo=bar"), {"channel": "CHANNELNAME"}),
        (("channel", "https://www.goodgame.ru/channel/CHANNELNAME"), {"channel": "CHANNELNAME"}),
        (("player", "https://goodgame.ru/player?CHANNELNAME"), {"channel": "CHANNELNAME"}),
        (("player", "https://www.goodgame.ru/player?CHANNELNAME"), {"channel": "CHANNELNAME"}),
    ]

    should_not_match = [
        "https://goodgame.ru/channel",
        "https://goodgame.ru/player",
    ]
