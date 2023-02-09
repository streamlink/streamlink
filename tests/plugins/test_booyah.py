from streamlink.plugins.booyah import Booyah
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlBooyah(PluginCanHandleUrl):
    __plugin__ = Booyah

    should_match = [
        "http://booyah.live/nancysp",
        "https://booyah.live/nancysp",
        "http://booyah.live/channels/21755518",
        "https://booyah.live/channels/21755518",
        "http://booyah.live/clips/13271208573492782667?source=2",
        "https://booyah.live/clips/13271208573492782667?source=2",
        "http://booyah.live/vods/13865237825203323136?source=2",
        "https://booyah.live/vods/13865237825203323136?source=2",
        "http://www.booyah.live/nancysp",
        "https://www.booyah.live/nancysp",
        "http://www.booyah.live/channels/21755518",
        "https://www.booyah.live/channels/21755518",
        "http://www.booyah.live/clips/13271208573492782667?source=2",
        "https://www.booyah.live/clips/13271208573492782667?source=2",
        "http://www.booyah.live/vods/13865237825203323136?source=2",
        "https://www.booyah.live/vods/13865237825203323136?source=2",
    ]

    should_not_match = [
        "http://booyah.live/",
        "https://booyah.live/",
        "http://www.booyah.live/",
        "https://www.booyah.live/",
    ]
