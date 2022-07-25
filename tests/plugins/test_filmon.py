import datetime
from unittest.mock import patch

import freezegun
import pytest

from streamlink import Streamlink
from streamlink.plugins.filmon import FilmOnAPI, FilmOnHLS, Filmon
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlFilmon(PluginCanHandleUrl):
    __plugin__ = Filmon

    should_match = [
        'http://www.filmon.tv/channel/grandstand-show',
        'http://www.filmon.tv/index/popout?channel_id=5510&quality=low',
        'http://www.filmon.tv/tv/channel/export?channel_id=5510&autoPlay=1',
        'http://www.filmon.tv/tv/channel/grandstand-show',
        'http://www.filmon.tv/tv/channel-4',
        'https://www.filmon.com/tv/bbc-news',
        'https://www.filmon.tv/tv/55',
        'http://www.filmon.tv/vod/view/10250-0-crime-boss',
        'http://www.filmon.tv/group/comedy',
    ]

    should_match_groups = [
        ('http://www.filmon.tv/channel/grandstand-show', (None, "grandstand-show", None)),
        ('http://www.filmon.tv/index/popout?channel_id=5510&quality=low', (None, '5510', None)),
        ('http://www.filmon.tv/tv/channel/export?channel_id=5510&autoPlay=1', (None, '5510', None)),
        ('http://www.filmon.tv/tv/channel/grandstand-show', (None, 'grandstand-show', None)),
        ('https://www.filmon.com/tv/bbc-news', (None, 'bbc-news', None)),
        ('https://www.filmon.com/tv/channel-4', (None, 'channel-4', None)),
        ('https://www.filmon.tv/tv/55', (None, '55', None)),
        ('http://www.filmon.tv/group/comedy', ('group/', 'comedy', None)),
        ('http://www.filmon.tv/vod/view/10250-0-crime-boss', (None, None, '10250-0-crime-boss')),
        ('http://www.filmon.tv/vod/view/10250-0-crime-boss/extra', (None, None, '10250-0-crime-boss')),
        ('http://www.filmon.tv/vod/view/10250-0-crime-boss?extra', (None, None, '10250-0-crime-boss')),
        ('http://www.filmon.tv/vod/view/10250-0-crime-boss&extra', (None, None, '10250-0-crime-boss')),
    ]


@pytest.fixture(scope="function")
def filmonhls():
    with freezegun.freeze_time(datetime.datetime(2000, 1, 1, 0, 0, 0, 0)), \
         patch("streamlink.plugins.filmon.FilmOnHLS._get_stream_data", return_value=[]):
        session = Streamlink()
        api = FilmOnAPI(session)
        yield FilmOnHLS(session, "http://fake/one.m3u8", api=api, channel="test")


def test_filmonhls_to_url(filmonhls):
    filmonhls.watch_timeout = datetime.datetime(2000, 1, 1, 0, 0, 0, 0).timestamp()
    assert filmonhls.to_url() == "http://fake/one.m3u8"


def test_filmonhls_to_url_updated(filmonhls):
    filmonhls.watch_timeout = datetime.datetime(1999, 12, 31, 23, 59, 59, 9999).timestamp()

    filmonhls._get_stream_data.return_value = [
        ("high", "http://fake/two.m3u8", datetime.datetime(2000, 1, 1, 0, 0, 0, 0).timestamp()),
    ]
    assert filmonhls.to_url() == "http://fake/two.m3u8"

    filmonhls.watch_timeout = datetime.datetime(1999, 12, 31, 23, 59, 59, 9999).timestamp()
    filmonhls._get_stream_data.return_value = [
        ("high", "http://another-fake/three.m3u8", datetime.datetime(2000, 1, 1, 0, 0, 0, 0).timestamp()),
    ]
    assert filmonhls.to_url() == "http://fake/three.m3u8"


def test_filmonhls_to_url_missing_quality(filmonhls):
    filmonhls.watch_timeout = datetime.datetime(1999, 12, 31, 23, 59, 59, 9999).timestamp()

    filmonhls._get_stream_data.return_value = [
        ("low", "http://fake/two.m3u8", datetime.datetime(2000, 1, 1, 0, 0, 0, 0).timestamp()),
    ]
    with pytest.raises(TypeError) as cm:
        filmonhls.to_url()
    assert str(cm.value) == "Stream has expired and cannot be translated to a URL"
