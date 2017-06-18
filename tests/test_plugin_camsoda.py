import unittest

from streamlink import Streamlink

try:
    from unittest.mock import patch, Mock
except ImportError:
    from mock import patch, Mock

from streamlink.plugins.camsoda import Camsoda
from streamlink.stream import HLSStream


class TestPluginCamsoda(unittest.TestCase):
    def setUp(self):
        self.session = Streamlink()
        self.plugin = Camsoda("https://www.camsoda.com/stream-name")

    def test_can_handle_url(self):
        # should match
        self.assertTrue(Camsoda.can_handle_url("https://www.camsoda.com/stream-name"))
        self.assertTrue(Camsoda.can_handle_url("https://www.camsoda.com/streamname"))
        self.assertTrue(Camsoda.can_handle_url("https://www.camsoda.com/username"))

        # shouldn't match
        self.assertFalse(Camsoda.can_handle_url("http://local.local/"))
        self.assertFalse(Camsoda.can_handle_url("http://localhost.localhost/"))

    def test_get_hls_url(self):
        api_data_video = {
            "token": "abcdefghijklmnopqrstuvwxyz123456",
            "app": "cam",
            "edge_servers": ["edge.server", "edge.server2"],
            "private_servers": ["priv.server", "priv.server2"],
            "mjpeg_server": "mjpeg.server",
            "stream_name": "username_enc4"
        }

        values = [
            {
                "api_data_user": {"user": {"chatstatus": "online"}},
                "server": "edge.server"
            }, {
                "api_data_user": {"user": {"chatstatus": "private"}},
                "server": "priv.server"
            }, {
                "api_data_user": {"user": {"chatstatus": "foobar"}},
                "server": "mjpeg.server"
            }
        ]
        for data in values:
            data_video = api_data_video
            data_user = data["api_data_user"]
            server = data["server"]

            HLS_URL_VIDEO = self.plugin._get_hls_url(data_user, data_video)
            HLS_URL_VIDEO_TEST = self.plugin.HLS_URL_VIDEO.format(server=server, app=data_video["app"], stream_name=data_video["stream_name"], token=data_video["token"])

            self.assertEqual(HLS_URL_VIDEO, HLS_URL_VIDEO_TEST)

    @patch('streamlink.plugins.camsoda.http')
    @patch('streamlink.plugins.camsoda.HLSStream')
    def test_get_streams(self, hlsstream, mock_http):
        hlsstream.parse_variant_playlist.return_value = {"test": HLSStream(self.session, "http://test.se/stream1")}

        streams = self.plugin.get_streams()

        self.assertTrue("test" in streams)
