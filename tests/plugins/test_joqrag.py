from streamlink.plugins.joqrag import JoqrAg
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlJoqrAg(PluginCanHandleUrl):
    __plugin__ = JoqrAg

    should_match = [
        "https://www.uniqueradio.jp/agplayer5/player.php",
        "https://www.uniqueradio.jp/agplayer5/inc-player-hls.php",
        "https://joqr.co.jp/ag/article/103760/",
        "https://www.joqr.co.jp/ag/article/103760/",
        "https://joqr.co.jp/qr/agdailyprogram/",
        "https://www.joqr.co.jp/qr/agdailyprogram/",
        "https://joqr.co.jp/qr/agregularprogram/",
        "https://www.joqr.co.jp/qr/agregularprogram/",
    ]

    should_not_match = [
        "https://uniqueradio.jp/agplayer5/player.php",
        "https://uniqueradio.jp/agplayer5/inc-player-hls.php",
        "https://www.joqr.co.jp/",
        "https://www.joqr.co.jp/qr/article/0/",
        "https://www.joqr.co.jp/ic/",
        "https://www.joqr.co.jp/ic/article/0/",
        "https://www.joqr.co.jp/qr/dailyprogram/",
        "https://www.joqr.co.jp/qr/regularprogram/",
    ]
