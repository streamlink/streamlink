from streamlink.plugins.cdnbg import CDNBG
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlCDNBG(PluginCanHandleUrl):
    __plugin__ = CDNBG

    should_match = [
        "http://bgonair.bg/tvonline",
        "http://bgonair.bg/tvonline/",
        "http://www.nova.bg/live",
        "http://nova.bg/live",
        "http://bnt.bg/live",
        "http://bnt.bg/live/bnt1",
        "http://bnt.bg/live/bnt2",
        "http://bnt.bg/live/bnt3",
        "http://bnt.bg/live/bnt4",
        "http://tv.bnt.bg/bnt1",
        "http://tv.bnt.bg/bnt2",
        "http://tv.bnt.bg/bnt3",
        "http://tv.bnt.bg/bnt4",
        "http://mu-vi.tv/LiveStreams/pages/Live.aspx",
        "http://live.bstv.bg/",
        "https://www.bloombergtv.bg/video",
        "https://i.cdn.bg/live/xfr3453g0d",
        "https://armymedia.bg/%d0%bd%d0%b0-%d0%b6%d0%b8%d0%b2%d0%be/",
    ]

    should_not_match = [
        "https://www.tvevropa.com",
        "http://www.kanal3.bg/live",
        "http://inlife.bg/",
        "http://videochanel.bstv.bg",
        "http://video.bstv.bg/",
        "http://bitelevision.com/live",
        "http://mmtvmusic.com/live/",
        "http://chernomore.bg/",
    ]
