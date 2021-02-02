from streamlink.plugins.rtpplay import RTPPlay
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlRTPPlay(PluginCanHandleUrl):
    __plugin__ = RTPPlay

    should_match = [
        'http://www.rtp.pt/play/',
        'https://www.rtp.pt/play/',
        'https://www.rtp.pt/play/direto/rtp1',
        'https://www.rtp.pt/play/direto/rtpmadeira',
    ]

    should_not_match = [
        'https://www.rtp.pt/programa/',
        'http://www.rtp.pt/programa/',
        'https://media.rtp.pt/',
        'http://media.rtp.pt/',
    ]
