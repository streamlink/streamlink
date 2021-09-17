import pytest

from streamlink.utils.rtmp import rtmpparse


@pytest.mark.parametrize("url,tcurl,playpath", [
    ("rtmp://testserver.com/app/playpath?arg=1", "rtmp://testserver.com:1935/app", "playpath?arg=1"),
    ("rtmp://testserver.com/long/app/playpath?arg=1", "rtmp://testserver.com:1935/long/app", "playpath?arg=1"),
    ("rtmp://testserver.com/app", "rtmp://testserver.com:1935/app", None),
])
def test_rtmpparse(url, tcurl, playpath):
    assert rtmpparse(url) == (tcurl, playpath)
