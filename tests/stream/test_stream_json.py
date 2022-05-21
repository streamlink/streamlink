from unittest.mock import Mock

import pytest
# noinspection PyUnresolvedReferences
from requests.utils import DEFAULT_ACCEPT_ENCODING  # type: ignore[attr-defined]

from streamlink import Streamlink
from streamlink.stream.dash import DASHStream
from streamlink.stream.file import FileStream
from streamlink.stream.hls import HLSStream
from streamlink.stream.http import HTTPStream
from streamlink.stream.stream import Stream


@pytest.fixture(scope="module")
def session():
    session = Streamlink()
    session.set_option("http-cookies", {"sessioncookiekey": "sessioncookieval"})
    session.set_option("http-headers", {"sessionheaderkey": "sessionheaderval"})
    session.set_option("http-query-params", {"sessionqueryparamkey": "sessionqueryparamval"})

    return session


@pytest.fixture(scope="module")
def common_args():
    return dict(
        params={"queryparamkey": "queryparamval"},
        headers={
            "User-Agent": "Test",
            "headerkey": "headerval",
        },
        cookies={"cookiekey": "cookieval"},
        unknown="invalid",
    )


@pytest.fixture(scope="module")
def expected_headers():
    return {
        "User-Agent": "Test",
        "Accept": "*/*",
        "Accept-Encoding": DEFAULT_ACCEPT_ENCODING,
        "Connection": "keep-alive",
        "Cookie": "sessioncookiekey=sessioncookieval; cookiekey=cookieval",
        "headerkey": "headerval",
        "sessionheaderkey": "sessionheaderval",
    }


def test_base_stream(session):
    stream = Stream(session)
    assert stream.__json__() == {
        "type": "stream",
    }
    assert stream.json == """{"type": "stream"}"""


def test_file_stream_path(session):
    stream = FileStream(session, "/path/to/file")
    assert stream.__json__() == {
        "type": "file",
        "path": "/path/to/file",
    }


def test_file_stream_handle(session):
    stream = FileStream(session, None, Mock())
    assert stream.__json__() == {
        "type": "file",
    }


def test_http_stream(session, common_args, expected_headers):
    stream = HTTPStream(session, "http://host/path?foo=bar", **common_args)
    assert stream.__json__() == {
        "type": "http",
        "url": "http://host/path?foo=bar&sessionqueryparamkey=sessionqueryparamval&queryparamkey=queryparamval",
        "method": "GET",
        "body": None,
        "headers": expected_headers,
    }


def test_hls_stream(session, common_args, expected_headers):
    stream = HLSStream(session, "http://host/stream.m3u8?foo=bar", **common_args)
    assert stream.__json__() == {
        "type": "hls",
        "url": "http://host/stream.m3u8?foo=bar&sessionqueryparamkey=sessionqueryparamval&queryparamkey=queryparamval",
        "headers": expected_headers,
    }


def test_hls_stream_master(session, common_args, expected_headers):
    stream = HLSStream(session, "http://host/stream.m3u8?foo=bar", "http://host/master.m3u8?foo=bar", **common_args)
    assert stream.__json__() == {
        "type": "hls",
        "url": "http://host/stream.m3u8?foo=bar&sessionqueryparamkey=sessionqueryparamval&queryparamkey=queryparamval",
        "master": "http://host/master.m3u8?foo=bar&sessionqueryparamkey=sessionqueryparamval&queryparamkey=queryparamval",
        "headers": expected_headers,
    }


def test_dash_stream(session, common_args):
    mpd = Mock(url=None)
    stream = DASHStream(session, mpd, **common_args)
    assert stream.__json__() == {
        "type": "dash",
    }


def test_dash_stream_url(session, common_args, expected_headers):
    # DASHStream requires an MPD instance as input:
    # The URL of the MPD instance was already prepared by DASHStream.parse_manifest, so copy this behavior here.
    # This test verifies that session params, headers, etc. are added to the JSON data, without duplicates.
    args = common_args.copy()
    args.update(url="http://host/stream.mpd?foo=bar")
    url = session.http.prepare_new_request(**args).url

    mpd = Mock(url=url)
    stream = DASHStream(session, mpd, **common_args)
    assert stream.__json__() == {
        "type": "dash",
        "url": "http://host/stream.mpd?foo=bar&sessionqueryparamkey=sessionqueryparamval&queryparamkey=queryparamval",
        "headers": expected_headers,
    }
