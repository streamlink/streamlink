from streamlink.plugins.vidio import Vidio
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlVidio(PluginCanHandleUrl):
    __plugin__ = Vidio

    should_match = [
        'https://www.vidio.com/live/204-sctv-tv-stream',
        'https://www.vidio.com/live/5075-dw-tv-stream',
        'https://www.vidio.com/watch/766861-5-rekor-fantastis-zidane-bersama-real-madrid',
    ]

    should_not_match = [
        'http://www.vidio.com',
        'https://www.vidio.com',
    ]
