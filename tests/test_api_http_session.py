import unittest
from unittest.mock import PropertyMock, call, patch

import requests

from streamlink.exceptions import PluginError
from streamlink.plugin.api.http_session import HTTPSession
from streamlink.plugin.api.useragents import FIREFOX


class TestPluginAPIHTTPSession(unittest.TestCase):
    def test_session_init(self):
        session = HTTPSession()
        self.assertEqual(session.headers.get("User-Agent"), FIREFOX)
        self.assertEqual(session.timeout, 20.0)
        self.assertIn("file://", session.adapters.keys())

    @patch("streamlink.plugin.api.http_session.time.sleep")
    @patch("streamlink.plugin.api.http_session.Session.request", side_effect=requests.Timeout)
    def test_read_timeout(self, mock_request, mock_sleep):
        session = HTTPSession()

        with self.assertRaises(PluginError) as cm:
            session.get("http://localhost/", timeout=123, retries=3, retry_backoff=2, retry_max_backoff=5)
        self.assertTrue(str(cm.exception).startswith("Unable to open URL: http://localhost/"))
        self.assertEqual(mock_request.mock_calls, [
            call("GET", "http://localhost/", headers={}, params={}, timeout=123, proxies={}, allow_redirects=True),
            call("GET", "http://localhost/", headers={}, params={}, timeout=123, proxies={}, allow_redirects=True),
            call("GET", "http://localhost/", headers={}, params={}, timeout=123, proxies={}, allow_redirects=True),
            call("GET", "http://localhost/", headers={}, params={}, timeout=123, proxies={}, allow_redirects=True),
        ])
        self.assertEqual(mock_sleep.mock_calls, [
            call(2),
            call(4),
            call(5)
        ])

    def test_json_encoding(self):
        json_str = "{\"test\": \"Α and Ω\"}"

        # encode the json string with each encoding and assert that the correct one is detected
        for encoding in ["UTF-32BE", "UTF-32LE", "UTF-16BE", "UTF-16LE", "UTF-8"]:
            with patch('requests.Response.content', new_callable=PropertyMock) as mock_content:
                mock_content.return_value = json_str.encode(encoding)
                res = requests.Response()

                self.assertEqual(HTTPSession.json(res), {"test": "\u0391 and \u03a9"})

    def test_json_encoding_override(self):
        json_text = "{\"test\": \"Α and Ω\"}".encode("cp949")

        with patch('requests.Response.content', new_callable=PropertyMock) as mock_content:
            mock_content.return_value = json_text
            res = requests.Response()
            res.encoding = "cp949"

            self.assertEqual(HTTPSession.json(res), {"test": "\u0391 and \u03a9"})
