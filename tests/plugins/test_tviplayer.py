from streamlink.plugins.tviplayer import TVIPlayer
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlTVIPlayer(PluginCanHandleUrl):
    __plugin__ = TVIPlayer

    should_match = [
        "https://tviplayer.iol.pt/direto/TVI24",
        "https://tviplayer.iol.pt/direto/TVI_AFRICA",
        "https://tviplayer.iol.pt/programa/prisioneira/5c890ae00cf2f1892ed73779/episodio/t2e219",
    ]

    should_not_match = [
        "https://tviplayer.iol.pt/programas/Exclusivos",
    ]
