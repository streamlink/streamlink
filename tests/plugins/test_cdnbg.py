import pytest

from streamlink.plugins.cdnbg import CDNBG

valid_urls = [
    ("http://bgonair.bg/tvonline",),
    ("http://bgonair.bg/tvonline/",),
    ("http://www.nova.bg/live",),
    ("http://nova.bg/live",),
    ("http://tv.bnt.bg/bnt1",),
    ("http://tv.bnt.bg/bnt2",),
    ("http://tv.bnt.bg/bnt3",),
    ("http://tv.bnt.bg/bnt4",),
    ("https://mmtvmusic.com/live/",),
    ("http://mu-vi.tv/LiveStreams/pages/Live.aspx",),
    ("http://live.bstv.bg/",),
    ("https://www.bloombergtv.bg/video",),
    ("https://i.cdn.bg/live/xfr3453g0d",)

]
invalid_urls = [
    ("http://www.tvcatchup.com/",),
    ("http://www.youtube.com/",),
    ("https://www.tvevropa.com",),
    ("http://www.kanal3.bg/live",),
    ("http://inlife.bg/",),
    ("http://videochanel.bstv.bg",),
    ("http://video.bstv.bg/",),
    ("http://bitelevision.com/live",)
]


@pytest.mark.parametrize(["url"], valid_urls)
def test_can_handle_url(url):
    assert CDNBG.can_handle_url(url), "url should be handled"


@pytest.mark.parametrize(["url"], invalid_urls)
def test_can_handle_url_negative(url):
    assert not CDNBG.can_handle_url(url), "url should not be handled"
