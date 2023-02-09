import unittest
from unittest.mock import ANY, MagicMock

from streamlink import Streamlink
from streamlink.plugins.ustreamtv import UStreamTV
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlUStreamTV(PluginCanHandleUrl):
    __plugin__ = UStreamTV

    should_match_groups = [
        (
            "https://www.ustream.tv/nasahdtv",
            {},
        ),
        (
            "https://www.ustream.tv/channel/6540154",
            {"channel_id": "6540154"},
        ),
        (
            "https://www.ustream.tv/channel/id/6540154",
            {"channel_id": "6540154"},
        ),
        (
            "https://www.ustream.tv/embed/6540154",
            {"channel_id": "6540154"},
        ),
        (
            "https://www.ustream.tv/recorded/132041157",
            {"video_id": "132041157"},
        ),
        (
            "https://www.ustream.tv/embed/recorded/132041157",
            {"video_id": "132041157"},
        ),
        (
            "https://www.ustream.tv/combined-embed/6540154",
            {"combined_channel_id": "6540154"},
        ),
        (
            "https://www.ustream.tv/combined-embed/6540154/video/132041157",
            {"combined_channel_id": "6540154", "combined_video_id": "132041157"},
        ),
        (
            "https://video.ibm.com/nasahdtv",
            {},
        ),
        (
            "https://video.ibm.com/recorded/132041157",
            {"video_id": "132041157"},
        ),
    ]


class TestPluginUStreamTV(unittest.TestCase):
    def test_arguments(self):
        from streamlink_cli.main import setup_plugin_args
        session = Streamlink()
        parser = MagicMock()
        plugins = parser.add_argument_group("Plugin Options")
        group = parser.add_argument_group("UStreamTV", parent=plugins)

        session.plugins = {
            "ustreamtv": UStreamTV,
        }

        setup_plugin_args(session, parser)

        group.add_argument.assert_called_with("--ustream-password", metavar="PASSWORD", help=ANY)
