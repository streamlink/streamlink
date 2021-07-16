from streamlink.plugins.tv4play import TV4Play
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlTV4Play(PluginCanHandleUrl):
    __plugin__ = TV4Play

    should_match = [
        'https://www.tv4play.se/program/robinson/del-26-sasong-2021/13299862',
        'https://www.tv4play.se/program/sverige-mot-norge/del-1-sasong-1/12490380',
        'https://www.tv4play.se/program/nyheterna/live/10378590',
        'https://www.fotbollskanalen.se/video/10395484/ghoddos-fullbordar-vandningen---ger-ofk-ledningen/',
    ]
