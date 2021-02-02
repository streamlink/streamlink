from streamlink.plugins.atresplayer import AtresPlayer
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlAtresPlayer(PluginCanHandleUrl):
    __plugin__ = AtresPlayer

    should_match = [
        'http://www.atresplayer.com/directos/antena3/',
        'http://www.atresplayer.com/directos/lasexta/',
        'https://www.atresplayer.com/directos/antena3/',
        'https://www.atresplayer.com/flooxer/programas/unas/temporada-1/dario-eme-hache-sindy-takanashi-entrevista_123/',
    ]
