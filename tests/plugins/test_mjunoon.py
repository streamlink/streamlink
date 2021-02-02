import unittest
from unittest.mock import ANY, Mock, call, patch

import requests_mock

from streamlink import Streamlink
from streamlink.plugins.mjunoon import Mjunoon
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlMjunoon(PluginCanHandleUrl):
    __plugin__ = Mjunoon

    should_match = [
        'https://mjunoon.tv/news-live',
        'http://mjunoon.tv/watch/some-long-vod-name23456',
        'https://www.mjunoon.tv/other-live',
        'https://www.mjunoon.tv/watch/something-else-2321',
    ]

    should_not_match = [
        'https://mjunoon.com',
    ]


class TestPluginMjunoon(unittest.TestCase):
    @patch('streamlink.plugins.mjunoon.HLSStream.parse_variant_playlist')
    def test_get_streams(self, parse_variant_playlist):
        session = Streamlink()
        Mjunoon.bind(session, "test")
        script_text = """
        <script id="playerScript"  src="playerAssets/js/player.js?v=2.2&streamUrl=https://vod.mjunoon.tv:8181/live/41/41.m3u8&streamUrl=https://vod.mjunoon.tv:8181/live/17/17.m3u8"></script>
        """  # noqa: E501
        parse_variant_playlist.items.return_value = [("test", Mock())]
        with requests_mock.Mocker() as rmock:
            rmock.get("https://mjunoon.tv/news-live", text=script_text)
            plugin = Mjunoon("https://mjunoon.tv/news-live")
            _ = list(plugin.streams())
            self.assertSequenceEqual(
                [call(ANY, "https://vod.mjunoon.tv:8181/live/41/41.m3u8", params=dict(id=1), verify=False),
                 call(ANY, "https://vod.mjunoon.tv:8181/live/17/17.m3u8", params=dict(id=2), verify=False)],
                [parse_variant_playlist.mock_calls[0], parse_variant_playlist.mock_calls[3]])
