import unittest

from streamlink import Streamlink

try:
    from unittest.mock import ANY, MagicMock, call
except ImportError:
    from mock import ANY, MagicMock, call
from streamlink.plugins.funimationnow import FunimationNow


class TestPluginFunimationNow(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            "http://www.funimation.com/anything",
            "http://www.funimation.com/anything123",
            "http://www.funimationnow.uk/anything",
            "http://www.funimationnow.uk/anything123",
        ]
        for url in should_match:
            self.assertTrue(FunimationNow.can_handle_url(url))

        should_not_match = [
            "https://www.youtube.com/v/aqz-KE-bpKQ",
        ]
        for url in should_not_match:
            self.assertFalse(FunimationNow.can_handle_url(url))

    def test_arguments(self):
        from streamlink_cli.main import setup_plugin_args
        session = Streamlink()
        parser = MagicMock()
        plugin_parser = MagicMock()
        parser.add_argument_group = MagicMock(return_value=plugin_parser)

        session.plugins = {
            'funimationnow': FunimationNow
        }

        setup_plugin_args(session, parser)
        self.assertSequenceEqual(plugin_parser.add_argument.mock_calls,
                                 [call('--funimation-email', help=ANY),
                                  call('--funimation-password', help=ANY),
                                  call('--funimation-language',
                                       choices=["en", "ja", "english", "japanese"],
                                       default="english", help=ANY),
                                  call('--funimation-mux-subtitles', action="store_true", help=ANY)])
