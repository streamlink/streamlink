from streamlink.plugins.goodgame import GoodGame
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlGoodGame(PluginCanHandleUrl):
    __plugin__ = GoodGame

    should_match_groups = [
        (("default", "https://goodgame.ru/CHANNELNAME"), {"name": "CHANNELNAME"}),
        (("default", "https://goodgame.ru/CHANNELNAME/"), {"name": "CHANNELNAME"}),
        (("default", "https://goodgame.ru/CHANNELNAME?foo=bar"), {"name": "CHANNELNAME"}),
        (("default", "https://www.goodgame.ru/CHANNELNAME"), {"name": "CHANNELNAME"}),
        (("channel", "https://goodgame.ru/channel/CHANNELNAME"), {"channel": "CHANNELNAME"}),
        (("channel", "https://goodgame.ru/channel/CHANNELNAME/"), {"channel": "CHANNELNAME"}),
        (("channel", "https://goodgame.ru/channel/CHANNELNAME?foo=bar"), {"channel": "CHANNELNAME"}),
        (("channel", "https://www.goodgame.ru/channel/CHANNELNAME"), {"channel": "CHANNELNAME"}),
        (("player", "https://goodgame.ru/player?1234"), {"id": "1234"}),
        (("player", "https://www.goodgame.ru/player?1234"), {"id": "1234"}),
    ]

    should_not_match = [
        "https://goodgame.ru/channel",
        "https://goodgame.ru/player",
    ]
