import unittest

from streamlink import Streamlink
from streamlink.plugin.api import HTTPSession
from streamlink.plugins.tvplayer import TVPlayer
from streamlink.stream import HLSStream
from tests.mock import patch, Mock, ANY, MagicMock, call


class TestPluginTVPlayer(unittest.TestCase):
    def setUp(self):
        self.session = Streamlink()
        self.session.http = MagicMock(HTTPSession)
        self.session.http.headers = {}

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

    @patch('streamlink.plugins.tvplayer.TVPlayer._get_stream_data')
    @patch('streamlink.plugins.tvplayer.HLSStream')
    def test_get_streams(self, hlsstream, mock_get_stream_data):
        mock_get_stream_data.return_value = {
            "response": {"stream": "http://test.se/stream1", "drm": None}
        }

        page_resp = Mock()
        page_resp.text = u"""
            <div class="full-bleed-container">
                <div class="container-fluid">
                    <div class="row">
                        <div class="col-xs-12">
                            <div id="live-player-root"
                                data-player-library="videojs"
                                data-player-id="ILWxqLKV91Ql8kF"
                                data-player-key="2Pw1Eg0Px3Gy9Jm3Ry8Ar5Bi5Vc5Nk"
                                data-player-uvid="139"
                                data-player-token="275c808a685a09d6e36d0253ab3765af"
                                data-player-expiry="1531958189"
                                data-player-poster=""
                                data-player-npaw='{"enableAnalytics":true,"username":"","extraparam.1":"TVPlayer","extraparam.2":"","extraparam.3":"free","extraparam.4":"","extraparam.5":"","extraparam.16":null,"content.isLive":true,"content.title":"BBC London News; Weather","content.title2":"","content.duration":"","content.metadata":{"uvid":"e3e45caf-79fe-3827-82b4-ecdfee52acfb","producer":"","status":"","genre":"","thumbnail":"https:\/\/d537y3nbkeq75.cloudfront.net\/tvp\/epg\/e3e45caf-79fe-3827-82b4-ecdfee52acfb.jpg?width=700&lang=en","asset-type":""},"title":"BBC London News; Weather","extraparam.7":"","extraparam.9":"e3e45caf-79fe-3827-82b4-ecdfee52acfb","extraparam.13":null,"extraparam.14":true,"extraparam.6":"","extraparam.8":""}'
                                data-requested-channel-id="739"
                                data-npaw-base-settings="%7B%22accountName%22%3A%22alchimie%22%2C%22data%22%3A%7B%22enableAnalytics%22%3Atrue%2C%22username%22%3A%22%22%2C%22extraparam.1%22%3A%22TVPlayer%22%2C%22extraparam.2%22%3A%22%22%2C%22extraparam.3%22%3A%22free%22%2C%22extraparam.4%22%3A%22%22%2C%22extraparam.5%22%3A%22%22%2C%22extraparam.16%22%3Anull%7D%7D"
                                data-play-button="/assets/tvplayer/images/dist/play-button-epg.svg"
                                data-update-url="/now-ajax"
                                data-timezone-name="Europe/London"
                                data-thumb-link-classes=""
                                data-theme-name="tvplayer"
                                data-base-entitlements="%5B%22free%22%5D"
                                data-has-identity="0"
                                data-require-identity-to-watch-free="1"
                                data-stream-type="live"
                                data-live-route="/watch/%25live_channel_id%25"
                            >
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        """

        self.session.http.get.return_value = page_resp
        hlsstream.parse_variant_playlist.return_value = {
            "test": HLSStream(self.session, "http://test.se/stream1")
        }

        TVPlayer.bind(self.session, "test.tvplayer")
        plugin = TVPlayer("http://tvplayer.com/watch/dave")

        streams = plugin.streams()

        self.assertTrue("test" in streams)

        # test the url is used correctly
        self.session.http.get.assert_called_with(
            "http://tvplayer.com/watch/dave"
        )
        # test that the correct API call is made
        mock_get_stream_data.assert_called_with(
            expiry="1531958189",
            key="2Pw1Eg0Px3Gy9Jm3Ry8Ar5Bi5Vc5Nk",
            token="275c808a685a09d6e36d0253ab3765af",
            uvid="139"
        )
        # test that the correct URL is used for the HLSStream
        hlsstream.parse_variant_playlist.assert_called_with(
            ANY,
            "http://test.se/stream1"
        )

    def test_get_invalid_page(self):
        page_resp = Mock()
        page_resp.text = u"""
            var validate = "foo";
            var resourceId = "1234";
        """
        self.session.http.get.return_value = page_resp

        TVPlayer.bind(self.session, "test.tvplayer")
        plugin = TVPlayer("http://tvplayer.com/watch/dave")

        streams = plugin.streams()

        self.assertEqual({}, streams)

        # test the url is used correctly

        self.session.http.get.assert_called_with(
            "http://tvplayer.com/watch/dave"
        )

    def test_arguments(self):
        from streamlink_cli.main import setup_plugin_args
        session = Streamlink()
        parser = MagicMock()
        plugin_parser = MagicMock()
        parser.add_argument_group = MagicMock(return_value=plugin_parser)

        session.plugins = {
            'tvplayer': TVPlayer
        }

        setup_plugin_args(session, parser)

        self.assertSequenceEqual(
            plugin_parser.add_argument.mock_calls,
            [
                call('--tvplayer-email', metavar="EMAIL", help=ANY),
                call('--tvplayer-password', metavar="PASSWORD", help=ANY)
            ],
        )
