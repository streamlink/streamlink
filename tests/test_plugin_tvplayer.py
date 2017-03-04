import json
import unittest

from streamlink import Streamlink

try:
    from unittest.mock import patch, Mock, ANY
except ImportError:
    from mock import patch, Mock, ANY
from streamlink.plugins.tvplayer import TVPlayer
from streamlink.stream import HLSStream


class TestPluginTVPlayer(unittest.TestCase):
    def setUp(self):
        self.session = Streamlink()

    def test_can_handle_url(self):
        # should match
        self.assertTrue(TVPlayer.can_handle_url("http://tvplayer.com/watch/"))
        self.assertTrue(TVPlayer.can_handle_url("http://www.tvplayer.com/watch/"))
        self.assertTrue(TVPlayer.can_handle_url("http://tvplayer.com/watch"))
        self.assertTrue(TVPlayer.can_handle_url("http://www.tvplayer.com/watch"))
        self.assertTrue(TVPlayer.can_handle_url("http://tvplayer.com/watch/dave"))
        self.assertTrue(TVPlayer.can_handle_url("http://www.tvplayer.com/watch/itv"))
        self.assertTrue(TVPlayer.can_handle_url("https://www.tvplayer.com/watch/itv"))
        self.assertTrue(TVPlayer.can_handle_url("https://tvplayer.com/watch/itv"))

        # shouldn't match
        self.assertFalse(TVPlayer.can_handle_url("http://www.tvplayer.com/"))
        self.assertFalse(TVPlayer.can_handle_url("http://www.tvcatchup.com/"))
        self.assertFalse(TVPlayer.can_handle_url("http://www.youtube.com/"))

    @patch('streamlink.plugins.tvplayer.http')
    @patch('streamlink.plugins.tvplayer.HLSStream')
    def test_get_streams(self, hlsstream, mock_http):
        api_data = {
            "tvplayer": {
                "status": "200 OK",
                "response": {
                    "stream": "http://test.se/stream1"
                }
            }
        }
        page_resp = Mock()
        page_resp.text = u"""
        var validate = "foo";
        var resourceId = "1234";
        var platform = "test";
        """
        api_resp = Mock()
        api_resp.text = json.dumps(api_data)
        mock_http.get.return_value = page_resp
        mock_http.post.return_value = api_resp
        mock_http.json.return_value = api_data["tvplayer"]["response"]
        hlsstream.parse_variant_playlist.return_value = {"test": HLSStream(self.session, "http://test.se/stream1")}

        plugin = TVPlayer("http://tvplayer.com/watch/dave")

        streams = plugin.get_streams()

        self.assertTrue("test" in streams)

        # test the url is used correctly
        mock_http.get.assert_called_with("http://tvplayer.com/watch/dave")
        # test that the correct API call is made
        mock_http.post.assert_called_with("http://api.tvplayer.com/api/v2/stream/live", data=dict(service=1,
                                                                                                  id=u"1234",
                                                                                                  validate=u"foo",
                                                                                                  platform=u"test",
                                                                                                  token=None))
        # test that the correct URL is used for the HLSStream
        hlsstream.parse_variant_playlist.assert_called_with(ANY, "http://test.se/stream1")

    @patch('streamlink.plugins.tvplayer.http')
    def test_get_invalid_page(self, mock_http):
        page_resp = Mock()
        page_resp.text = u"""
        var validate = "foo";
        var resourceId = "1234";
        """
        mock_http.get.return_value = page_resp

        plugin = TVPlayer("http://tvplayer.com/watch/dave")

        streams = plugin.get_streams()

        self.assertEqual({}, streams)

        # test the url is used correctly

        mock_http.get.assert_called_with("http://tvplayer.com/watch/dave")
