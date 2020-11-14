import unittest
from unittest.mock import ANY, MagicMock

from streamlink import Streamlink
from streamlink.plugins.ustreamtv import UStreamTV


class TestPluginUStreamTV(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            "http://www.ustream.tv/streamlink",
            "http://www.ustream.tv/channel/id/1234",
            "http://www.ustream.tv/embed/1234",
            "http://www.ustream.tv/recorded/6543",
            "http://www.ustream.tv/embed/recorded/6543",
            "https://video.ibm.com/channel/H5rQLwmTGrW",
            "https://video.ibm.com/recorded/124680279",
        ]
        for url in should_match:
            self.assertTrue(UStreamTV.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            "https://www.youtube.com/v/aqz-KE-bpKQ",
        ]
        for url in should_not_match:
            self.assertFalse(UStreamTV.can_handle_url(url))

    def test_arguments(self):
        from streamlink_cli.main import setup_plugin_args
        session = Streamlink()
        parser = MagicMock()
        group = parser.add_argument_group("Plugin Options").add_argument_group("UStreamTV")

        session.plugins = {
            'ustreamtv': UStreamTV
        }

        setup_plugin_args(session, parser)

        group.add_argument.assert_called_with('--ustream-password', metavar="PASSWORD", help=ANY)
