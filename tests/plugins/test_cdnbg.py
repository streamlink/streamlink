from streamlink.plugins.cdnbg import CDNBG
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlCDNBG(PluginCanHandleUrl):
    __plugin__ = CDNBG

    should_match_groups = [
        (("bgonair", "http://bgonair.bg/tvonline"), {}),
        (("bgonair", "http://bgonair.bg/tvonline/"), {}),
        (("nova", "http://www.nova.bg/live"), {}),
        (("nova", "http://nova.bg/live"), {}),
        (("bnt", "http://bnt.bg/live"), {}),
        (("bnt", "http://bnt.bg/live/bnt1"), {}),
        (("bnt", "http://bnt.bg/live/bnt2"), {}),
        (("bnt", "http://bnt.bg/live/bnt3"), {}),
        (("bnt", "http://bnt.bg/live/bnt4"), {}),
        (("bnt", "http://tv.bnt.bg/bnt1"), {}),
        (("bnt", "http://tv.bnt.bg/bnt2"), {}),
        (("bnt", "http://tv.bnt.bg/bnt3"), {}),
        (("bnt", "http://tv.bnt.bg/bnt4"), {}),
        (("mu-vi", "http://mu-vi.tv/LiveStreams/pages/Live.aspx"), {}),
        (("bstv", "http://live.bstv.bg/"), {}),
        (("bloombergtv", "https://www.bloombergtv.bg/video"), {}),
        (("cdnbg", "https://i.cdn.bg/live/xfr3453g0d"), {}),
        (("armymedia", "https://armymedia.bg/%d0%bd%d0%b0-%d0%b6%d0%b8%d0%b2%d0%be/"), {}),
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
