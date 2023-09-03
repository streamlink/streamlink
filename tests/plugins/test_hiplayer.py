from streamlink.plugins.hiplayer import HiPlayer
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlHiPlayer(PluginCanHandleUrl):
    __plugin__ = HiPlayer

    should_match = [
        ("alwasatly", "https://alwasat.ly/live"),
        ("mediagovkw", "https://www.media.gov.kw/LiveTV.aspx?PanChannel=KTV1"),
        ("mediagovkw", "https://www.media.gov.kw/LiveTV.aspx?PanChannel=KTVSports"),
    ]
