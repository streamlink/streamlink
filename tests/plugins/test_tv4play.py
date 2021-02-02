from streamlink.plugins.tv4play import TV4Play
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlTV4Play(PluginCanHandleUrl):
    __plugin__ = TV4Play

    should_match = [
        'https://www.tv4play.se/program/fridas-vm-resa/10000884',
        'https://www.tv4play.se/program/monk/3938989',
        'https://www.tv4play.se/program/nyheterna/10378590',
        'https://www.fotbollskanalen.se/video/10395484/ghoddos-fullbordar-vandningen---ger-ofk-ledningen/',
    ]
