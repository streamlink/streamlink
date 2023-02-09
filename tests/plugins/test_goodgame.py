from streamlink.plugins.goodgame import GoodGame
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlGoodGame(PluginCanHandleUrl):
    __plugin__ = GoodGame

    should_match = [
        "https://goodgame.ru/channel/ABC_ABC/#autoplay",
        "https://goodgame.ru/channel/ABC123ABC/#autoplay",
        "https://goodgame.ru/channel/ABC/#autoplay",
        "https://goodgame.ru/channel/123ABC123/#autoplay",
    ]
