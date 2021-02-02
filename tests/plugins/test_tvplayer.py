import unittest
from unittest.mock import ANY, MagicMock, Mock, call, patch

from streamlink import Streamlink
from streamlink.plugin.api import HTTPSession
from streamlink.plugins.tvplayer import TVPlayer
from streamlink.stream import HLSStream
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlTVPlayer(PluginCanHandleUrl):
    __plugin__ = TVPlayer

    should_match = [
        "http://tvplayer.com/watch/",
        "http://www.tvplayer.com/watch/",
        "http://tvplayer.com/watch",
        "http://www.tvplayer.com/watch",
        "http://www.tvplayer.com/uk/watch",
        "http://tvplayer.com/watch/dave",
        "http://tvplayer.com/uk/watch/dave",
        "http://www.tvplayer.com/watch/itv",
        "http://www.tvplayer.com/uk/watch/itv",
        "https://www.tvplayer.com/watch/itv",
        "https://www.tvplayer.com/uk/watch/itv",
        "https://tvplayer.com/watch/itv",
        "https://tvplayer.com/uk/watch/itv",
    ]

    should_not_match = [
        "http://www.tvplayer.com/"
    ]


class TestPluginTVPlayer(unittest.TestCase):
    def setUp(self):
        self.session = Streamlink()
        self.session.http = MagicMock(HTTPSession)
        self.session.http.headers = {}

    @patch('streamlink.plugins.tvplayer.TVPlayer._get_stream_data')
    @patch('streamlink.plugins.tvplayer.HLSStream')
    def test_get_streams(self, hlsstream, mock_get_stream_data):
        mock_get_stream_data.return_value = {
            "response": {"stream": "http://test.se/stream1", "drm": None}
        }

        page_resp = Mock()
        page_resp.text = """
            <div class="col-xs-12">
                <div id="live-player-root"
                    data-player-library="videojs"
                    data-player-id="ILWxqLKV91Ql8kF"
                    data-player-key="2Pw1Eg0Px3Gy9Jm3Ry8Ar5Bi5Vc5Nk"
                    data-player-uvid="139"
                    data-player-token="275c808a685a09d6e36d0253ab3765af"
                    data-player-expiry="1531958189"
                    data-player-poster=""
                    data-requested-channel-id="139"
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
        page_resp.text = """
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
        group = parser.add_argument_group("Plugin Options").add_argument_group("TVPlayer")

        session.plugins = {
            'tvplayer': TVPlayer
        }

        setup_plugin_args(session, parser)

        self.assertSequenceEqual(
            group.add_argument.mock_calls,
            [
                call('--tvplayer-email', metavar="EMAIL", help=ANY),
                call('--tvplayer-password', metavar="PASSWORD", help=ANY)
            ],
        )
