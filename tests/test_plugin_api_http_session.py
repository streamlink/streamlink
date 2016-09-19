import unittest

from streamlink.exceptions import PluginError
from streamlink.plugin.api.http_session import HTTPSession


class TestPluginAPIHTTPSession(unittest.TestCase):
    def test_read_timeout(self):
        session = HTTPSession()

        def stream_data():
            res = session.get("http://httpbin.org/delay/6",
                              timeout=3, stream=True)
            next(res.iter_content(8192))


        self.assertRaises(PluginError, stream_data)

if __name__ == "__main__":
    unittest.main()
