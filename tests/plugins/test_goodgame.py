from streamlink.plugins.goodgame import GoodGame
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlGoodGame(PluginCanHandleUrl):
    __plugin__ = GoodGame

    should_match_groups = [
        (("default", "https://goodgame.ru/CHANNELNAME"), {"channel": "CHANNELNAME"}),
        (("default", "https://goodgame.ru/CHANNELNAME/"), {"channel": "CHANNELNAME"}),
        (("default", "https://goodgame.ru/CHANNELNAME?foo=bar"), {"channel": "CHANNELNAME"}),
        (("default", "https://www.goodgame.ru/CHANNELNAME"), {"channel": "CHANNELNAME"}),
        (("player", "https://goodgame.ru/player?CHANNELID"), {"channel_id": "CHANNELID"}),
        (("player", "https://www.goodgame.ru/player?CHANNELID"), {"channel_id": "CHANNELID"}),
    ]

    should_not_match = [
        "https://goodgame.ru/player?",
    ]
