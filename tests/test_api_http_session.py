import unittest
from unittest.mock import PropertyMock, call, patch

import pytest
import requests

from streamlink.exceptions import PluginError
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


class TestPluginAPIHTTPSession(unittest.TestCase):
    def test_session_init(self):
        session = HTTPSession()
        assert session.headers.get("User-Agent") == FIREFOX
        assert session.timeout == 20.0
        assert "file://" in session.adapters.keys()

    @patch("streamlink.plugin.api.http_session.time.sleep")
    @patch("streamlink.plugin.api.http_session.Session.request", side_effect=requests.Timeout)
    def test_read_timeout(self, mock_request, mock_sleep):
        session = HTTPSession()

        with pytest.raises(PluginError, match=r"^Unable to open URL: http://localhost/"):
            session.get("http://localhost/", timeout=123, retries=3, retry_backoff=2, retry_max_backoff=5)
        assert mock_request.mock_calls == [
            call("GET", "http://localhost/", headers={}, params={}, timeout=123, proxies={}, allow_redirects=True),
            call("GET", "http://localhost/", headers={}, params={}, timeout=123, proxies={}, allow_redirects=True),
            call("GET", "http://localhost/", headers={}, params={}, timeout=123, proxies={}, allow_redirects=True),
            call("GET", "http://localhost/", headers={}, params={}, timeout=123, proxies={}, allow_redirects=True),
        ]
        assert mock_sleep.mock_calls == [
            call(2),
            call(4),
            call(5),
        ]

    def test_json_encoding(self):
        json_str = "{\"test\": \"Α and Ω\"}"

        # encode the json string with each encoding and assert that the correct one is detected
        for encoding in ["UTF-32BE", "UTF-32LE", "UTF-16BE", "UTF-16LE", "UTF-8"]:
            with patch("requests.Response.content", new_callable=PropertyMock) as mock_content:
                mock_content.return_value = json_str.encode(encoding)
                res = requests.Response()

                assert HTTPSession.json(res) == {"test": "Α and Ω"}

    def test_json_encoding_override(self):
        json_text = "{\"test\": \"Α and Ω\"}".encode("cp949")

        with patch("requests.Response.content", new_callable=PropertyMock) as mock_content:
            mock_content.return_value = json_text
            res = requests.Response()
            res.encoding = "cp949"

            assert HTTPSession.json(res) == {"test": "Α and Ω"}
