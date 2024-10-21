from unittest.mock import Mock, call

import pytest

from streamlink.plugins.http import HTTPStreamPlugin
from streamlink.session import Streamlink
from streamlink.stream.http import HTTPStream
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlHTTPStreamPlugin(PluginCanHandleUrl):
    __plugin__ = HTTPStreamPlugin

    should_match_groups = [
        # explicit HTTPStream URLs
        ("httpstream://example.com/foo", {"url": "example.com/foo"}),
        ("httpstream://http://example.com/foo", {"url": "http://example.com/foo"}),
        ("httpstream://https://example.com/foo", {"url": "https://example.com/foo"}),
        # optional parameters
        ("httpstream://example.com/foo abc=def", {"url": "example.com/foo", "params": "abc=def"}),
        ("httpstream://http://example.com/foo abc=def", {"url": "http://example.com/foo", "params": "abc=def"}),
        ("httpstream://https://example.com/foo abc=def", {"url": "https://example.com/foo", "params": "abc=def"}),
    ]

    should_not_match = [
        # missing parameters
        "httpstream://example.com/foo ",
    ]


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("httpstream://example.com/foo", "https://example.com/foo"),
        ("httpstream://http://example.com/foo", "http://example.com/foo"),
        ("httpstream://https://example.com/foo", "https://example.com/foo"),
    ],
)
def test_get_streams(
    monkeypatch: pytest.MonkeyPatch,
    session: Streamlink,
    url: str,
    expected: str,
):
    mock_httpstream_init = Mock(return_value=None)
    monkeypatch.setattr("streamlink.stream.http.HTTPStream.__init__", mock_httpstream_init)

    plugin = HTTPStreamPlugin(session, url)
    result = plugin.streams()
    result.pop("worst", None)
    result.pop("best", None)

    assert list(result.keys()) == ["live"]
    assert isinstance(result["live"], HTTPStream)
    assert mock_httpstream_init.call_args_list == [call(session, expected)]


def test_parameters(monkeypatch: pytest.MonkeyPatch, session: Streamlink):
    mock_httpstream_init = Mock(return_value=None)
    monkeypatch.setattr("streamlink.stream.http.HTTPStream.__init__", mock_httpstream_init)

    plugin = HTTPStreamPlugin(
        session,
        (
            "httpstream://example.com/foo"
            + " auth=('foo', 'bar')"
            + " verify=False"
            + " referer=https://example2.com/bar"
            + " params={'key': 'a value'}"
        ),
    )
    plugin.streams()

    assert mock_httpstream_init.call_args_list == [
        call(
            session,
            "https://example.com/foo",
            auth=("foo", "bar"),
            verify=False,
            referer="https://example2.com/bar",
            params={"key": "a value"},
        ),
    ]
