from unittest.mock import Mock

import pytest

from streamlink.stream.dash import DASHStream
from streamlink.stream.file import FileStream
from streamlink.stream.hls import HLSStream
from streamlink.stream.http import HTTPStream
from streamlink.stream.stream import Stream


@pytest.fixture(scope="module")
def common_args():
    return dict(
        params={"queryparamkey": "queryparamval"},
        unknown="invalid",
    )


def test_base_stream(session):
    stream = Stream(session)
    with pytest.raises(TypeError) as cm:
        stream.to_url()
    assert str(cm.value) == "<Stream [stream]> cannot be translated to a URL"
    with pytest.raises(TypeError) as cm:
        stream.to_manifest_url()
    assert str(cm.value) == "<Stream [stream]> cannot be translated to a manifest URL"


def test_file_stream_handle(session):
    stream = FileStream(session, None, Mock())
    with pytest.raises(TypeError) as cm:
        stream.to_url()
    assert str(cm.value) == "<FileStream [file]> cannot be translated to a URL"
    with pytest.raises(TypeError) as cm:
        stream.to_manifest_url()
    assert str(cm.value) == "<FileStream [file]> cannot be translated to a manifest URL"


def test_file_stream_path(session):
    stream = FileStream(session, "/path/to/file")
    assert stream.to_url() == "/path/to/file"
    with pytest.raises(TypeError) as cm:
        stream.to_manifest_url()
    assert str(cm.value) == "<FileStream [file]> cannot be translated to a manifest URL"


def test_http_stream(session, common_args):
    stream = HTTPStream(session, "http://host/stream?foo=bar", **common_args)
    assert stream.to_url() == "http://host/stream?foo=bar&queryparamkey=queryparamval"
    with pytest.raises(TypeError) as cm:
        stream.to_manifest_url()
    assert str(cm.value) == "<HTTPStream [http]> cannot be translated to a manifest URL"


def test_hls_stream(session, common_args):
    stream = HLSStream(session, "http://host/stream.m3u8?foo=bar", **common_args)
    assert stream.to_url() == "http://host/stream.m3u8?foo=bar&queryparamkey=queryparamval"
    with pytest.raises(TypeError) as cm:
        stream.to_manifest_url()
    assert str(cm.value) == "<HLSStream [hls]> cannot be translated to a manifest URL"


def test_hls_stream_master(session, common_args):
    stream = HLSStream(session, "http://host/stream.m3u8?foo=bar", "http://host/master.m3u8?foo=bar", **common_args)
    assert stream.to_url() == "http://host/stream.m3u8?foo=bar&queryparamkey=queryparamval"
    assert stream.to_manifest_url() == "http://host/master.m3u8?foo=bar&queryparamkey=queryparamval"


def test_dash_stream(session):
    mpd = Mock(url=None)
    stream = DASHStream(session, mpd)
    with pytest.raises(TypeError) as cm:
        stream.to_url()
    assert str(cm.value) == "<DASHStream [dash]> cannot be translated to a URL"
    with pytest.raises(TypeError) as cm:
        stream.to_manifest_url()
    assert str(cm.value) == "<DASHStream [dash]> cannot be translated to a manifest URL"


def test_dash_stream_url(session, common_args):
    # DASHStream requires an MPD instance as input:
    # The URL of the MPD instance was already prepared by DASHStream.parse_manifest, so copy this behavior here.
    # This test verifies that session params are added to the URL, without duplicates.
    args = common_args.copy()
    args.update(url="http://host/stream.mpd?foo=bar")
    url = session.http.prepare_new_request(**args).url
    mpd = Mock(url=url)
    stream = DASHStream(session, mpd, **common_args)
    assert stream.to_url() == "http://host/stream.mpd?foo=bar&queryparamkey=queryparamval"
    with pytest.raises(TypeError) as cm:
        stream.to_manifest_url()
    assert str(cm.value) == "<DASHStream [dash]> cannot be translated to a manifest URL"
