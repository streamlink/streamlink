import unittest

from streamlink import Streamlink
from streamlink.plugins.stream import StreamURL
from streamlink.plugin.plugin import stream_weight
from streamlink.stream import *


class TestPluginStream(unittest.TestCase):
    def setUp(self):
        self.session = Streamlink()

    def assertDictHas(self, a, b):
        for key, value in a.items():
            self.assertEqual(b[key], value)

    def _test_akamaihd(self, surl, url):
        channel = self.session.resolve_url(surl)
        streams = channel.get_streams()

        self.assertTrue("live" in streams)

        stream = streams["live"]
        self.assertTrue(isinstance(stream, AkamaiHDStream))
        self.assertEqual(stream.url, url)

    def _test_hls(self, surl, url):
        channel = self.session.resolve_url(surl)
        streams = channel.get_streams()

        self.assertTrue("live" in streams)

        stream = streams["live"]
        self.assertTrue(isinstance(stream, HLSStream))
        self.assertEqual(stream.url, url)

    def _test_rtmp(self, surl, url, params):
        channel = self.session.resolve_url(surl)
        streams = channel.get_streams()

        self.assertTrue("live" in streams)

        stream = streams["live"]
        self.assertTrue(isinstance(stream, RTMPStream))
        self.assertEqual(stream.params["rtmp"], url)
        self.assertDictHas(params, stream.params)

    def _test_http(self, surl, url, params):
        channel = self.session.resolve_url(surl)
        streams = channel.get_streams()

        self.assertTrue("live" in streams)

        stream = streams["live"]
        self.assertTrue(isinstance(stream, HTTPStream))
        self.assertEqual(stream.url, url)
        self.assertDictHas(params, stream.args)

    def test_plugin_rtmp(self):
        self._test_rtmp("rtmp://hostname.se/stream",
                        "rtmp://hostname.se/stream", dict())

        self._test_rtmp("rtmp://hostname.se/stream live=1 qarg='a \\'string' noq=test",
                        "rtmp://hostname.se/stream", dict(live=True, qarg='a \'string', noq="test"))

        self._test_rtmp("rtmp://hostname.se/stream live=1 num=47",
                        "rtmp://hostname.se/stream", dict(live=True, num=47))

        self._test_rtmp("rtmp://hostname.se/stream conn=['B:1','S:authMe','O:1','NN:code:1.23','NS:flag:ok','O:0']",
                        "rtmp://hostname.se/stream",
                        dict(conn=['B:1', 'S:authMe', 'O:1', 'NN:code:1.23', 'NS:flag:ok', 'O:0']))

    def test_plugin_hls(self):
        self._test_hls("hls://https://hostname.se/playlist.m3u8",
                       "https://hostname.se/playlist.m3u8")

        self._test_hls("hls://hostname.se/playlist.m3u8",
                       "http://hostname.se/playlist.m3u8")

    def test_plugin_akamaihd(self):
        self._test_akamaihd("akamaihd://http://hostname.se/stream",
                            "http://hostname.se/stream")

        self._test_akamaihd("akamaihd://hostname.se/stream",
                            "http://hostname.se/stream")

    def test_plugin_http(self):
        self._test_http("httpstream://http://hostname.se/auth.php auth=('test','test2')",
                        "http://hostname.se/auth.php", dict(auth=("test", "test2")))

        self._test_http("httpstream://hostname.se/auth.php auth=('test','test2')",
                        "http://hostname.se/auth.php", dict(auth=("test", "test2")))

        self._test_http("httpstream://https://hostname.se/auth.php verify=False params={'key': 'a value'}",
                        "https://hostname.se/auth.php?key=a+value", dict(verify=False, params=dict(key='a value')))

    def test_parse_params(self):
        self.assertEqual(
            dict(verify=False, params=dict(key="a value")),
            StreamURL._parse_params("""verify=False params={'key': 'a value'}""")
        )
        self.assertEqual(
            dict(verify=False),
            StreamURL._parse_params("""verify=False""")
        )
        self.assertEqual(
            dict(conn=['B:1', 'S:authMe', 'O:1', 'NN:code:1.23', 'NS:flag:ok', 'O:0']),
            StreamURL._parse_params(""""conn=['B:1', 'S:authMe', 'O:1', 'NN:code:1.23', 'NS:flag:ok', 'O:0']""")
        )

    def test_stream_weight(self):
        self.assertEqual(
            (720, "pixels"),
            stream_weight("720p"))
        self.assertEqual(
            (721, "pixels"),
            stream_weight("720p+"))
        self.assertEqual(
            (780, "pixels"),
            stream_weight("720p60"))

        self.assertTrue(
            stream_weight("720p+") > stream_weight("720p"))
        self.assertTrue(
            stream_weight("720p") == stream_weight("720p"))
        self.assertTrue(
            stream_weight("720p_3000k") > stream_weight("720p_2500k"))
        self.assertTrue(
            stream_weight("720p60_3000k") > stream_weight("720p_3000k"))
        self.assertTrue(
            stream_weight("720p_3000k") < stream_weight("720p+_3000k"))

        self.assertTrue(
            stream_weight("3000k") > stream_weight("2500k"))


if __name__ == "__main__":
    unittest.main()
