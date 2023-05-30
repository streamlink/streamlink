from typing import Optional
from unittest.mock import Mock, PropertyMock, call

import pytest
import requests

from streamlink.exceptions import PluginError, StreamlinkDeprecationWarning
from streamlink.plugin.api.http_session import HTTPSession
from streamlink.plugin.api.useragents import FIREFOX


class TestUrllib3Overrides:
    @pytest.fixture(scope="class")
    def httpsession(self) -> HTTPSession:
        return HTTPSession()

    @pytest.mark.parametrize(("url", "expected", "assertion"), [
        ("https://foo/bar%3F?baz%21", "https://foo/bar%3F?baz%21", "Keeps encoded reserved characters"),
        ("https://foo/%62%61%72?%62%61%7A", "https://foo/bar?baz", "Decodes encoded unreserved characters"),
        ("https://foo/bär?bäz", "https://foo/b%C3%A4r?b%C3%A4z", "Encodes other characters"),
        ("https://foo/b%c3%a4r?b%c3%a4z", "https://foo/b%c3%a4r?b%c3%a4z", "Keeps percent-encodings with lowercase characters"),
        ("https://foo/b%C3%A4r?b%C3%A4z", "https://foo/b%C3%A4r?b%C3%A4z", "Keeps percent-encodings with uppercase characters"),
        ("https://foo/%?%", "https://foo/%25?%25", "Empty percent-encodings without valid encodings"),
        ("https://foo/%0?%0", "https://foo/%250?%250", "Incomplete percent-encodings without valid encodings"),
        ("https://foo/%zz?%zz", "https://foo/%25zz?%25zz", "Invalid percent-encodings without valid encodings"),
        ("https://foo/%3F%?%3F%", "https://foo/%253F%25?%253F%25", "Empty percent-encodings with valid encodings"),
        ("https://foo/%3F%0?%3F%0", "https://foo/%253F%250?%253F%250", "Incomplete percent-encodings with valid encodings"),
        ("https://foo/%3F%zz?%3F%zz", "https://foo/%253F%25zz?%253F%25zz", "Invalid percent-encodings with valid encodings"),
    ])
    def test_encode_invalid_chars(self, httpsession: HTTPSession, url: str, expected: str, assertion: str):
        req = requests.Request(method="GET", url=url)
        prep = httpsession.prepare_request(req)
        assert prep.url == expected, assertion


class TestHTTPSession:
    def test_session_init(self):
        session = HTTPSession()
        assert session.headers.get("User-Agent") == FIREFOX
        assert session.timeout == 20.0
        assert "file://" in session.adapters.keys()

    def test_read_timeout(self, monkeypatch: pytest.MonkeyPatch):
        mock_sleep = Mock()
        mock_request = Mock(side_effect=requests.Timeout)
        monkeypatch.setattr("streamlink.plugin.api.http_session.time.sleep", mock_sleep)
        monkeypatch.setattr("streamlink.plugin.api.http_session.Session.request", mock_request)

        session = HTTPSession()
        with pytest.raises(PluginError, match=r"^Unable to open URL: http://localhost/"):
            session.get("http://localhost/", timeout=123, retries=3, retry_backoff=2, retry_max_backoff=5)

        assert mock_request.call_args_list == [
            call("GET", "http://localhost/", headers={}, params={}, timeout=123, proxies={}, allow_redirects=True),
            call("GET", "http://localhost/", headers={}, params={}, timeout=123, proxies={}, allow_redirects=True),
            call("GET", "http://localhost/", headers={}, params={}, timeout=123, proxies={}, allow_redirects=True),
            call("GET", "http://localhost/", headers={}, params={}, timeout=123, proxies={}, allow_redirects=True),
        ]
        assert mock_sleep.call_args_list == [
            call(2),
            call(4),
            call(5),
        ]

    @pytest.mark.parametrize("encoding", ["UTF-32BE", "UTF-32LE", "UTF-16BE", "UTF-16LE", "UTF-8"])
    def test_determine_json_encoding(self, recwarn: pytest.WarningsRecorder, encoding: str):
        data = "Hello world, Γειά σου Κόσμε, こんにちは世界".encode(encoding)
        assert HTTPSession.determine_json_encoding(data) == encoding
        assert [(record.category, str(record.message)) for record in recwarn.list] == [
            (StreamlinkDeprecationWarning, "Deprecated HTTPSession.determine_json_encoding() call"),
        ]

    @pytest.mark.parametrize(("encoding", "override"), [
        ("utf-32-be", None),
        ("utf-32-le", None),
        ("utf-16-be", None),
        ("utf-16-le", None),
        ("utf-8", None),
        # With byte order mark (BOM)
        ("utf-16", None),
        ("utf-32", None),
        ("utf-8-sig", None),
        # Override
        ("utf-8", "utf-8"),
        ("cp949", "cp949"),
    ])
    def test_json(self, monkeypatch: pytest.MonkeyPatch, encoding: str, override: Optional[str]):
        mock_content = PropertyMock(return_value="{\"test\": \"Α and Ω\"}".encode(encoding))
        monkeypatch.setattr("requests.Response.content", mock_content)

        res = requests.Response()
        res.encoding = override

        assert HTTPSession.json(res) == {"test": "Α and Ω"}
