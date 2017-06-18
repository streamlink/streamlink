# coding=utf-8
import unittest

import requests

try:
    from unittest.mock import patch, PropertyMock
except ImportError:
    from mock import patch, PropertyMock

from streamlink.exceptions import PluginError
from streamlink.plugin.api.http_session import HTTPSession


class TestPluginAPIHTTPSession(unittest.TestCase):
    @patch('requests.sessions.Session.send')
    def test_read_timeout(self, mock_send):
        mock_send.side_effect = IOError
        session = HTTPSession()

        def stream_data():
            res = session.get("http://httpbin.org/delay/6",
                              timeout=3, stream=True)
            next(res.iter_content(8192))

        self.assertRaises(PluginError, stream_data)

    def test_json_encoding(self):
        json_str = u"{\"test\": \"Α and Ω\"}"

        # encode the json string with each encoding and assert that the correct one is detected
        for encoding in ["UTF-32BE", "UTF-32LE", "UTF-16BE", "UTF-16LE", "UTF-8"]:
            with patch('requests.Response.content', new_callable=PropertyMock) as mock_content:
                mock_content.return_value = json_str.encode(encoding)
                res = requests.Response()

                self.assertEqual(HTTPSession.json(res), {u"test": u"\u0391 and \u03a9"})

    def test_json_encoding_override(self):
        json_text = u"{\"test\": \"Α and Ω\"}".encode("cp949")

        with patch('requests.Response.content', new_callable=PropertyMock) as mock_content:
            mock_content.return_value = json_text
            res = requests.Response()
            res.encoding = "cp949"

            self.assertEqual(HTTPSession.json(res), {u"test": u"\u0391 and \u03a9"})


if __name__ == "__main__":
    unittest.main()
