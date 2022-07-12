import unittest
from unittest.mock import ANY, MagicMock, call

from streamlink import Streamlink
from streamlink.plugins.funimationnow import FunimationNow
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlFunimationNow(PluginCanHandleUrl):
    __plugin__ = FunimationNow

    should_match = [
        "http://www.funimation.com/anything",
        "http://www.funimation.com/anything123",
        "http://www.funimationnow.uk/anything",
        "http://www.funimationnow.uk/anything123",
    ]


class TestPluginFunimationNow(unittest.TestCase):
    def test_arguments(self):
        from streamlink_cli.main import setup_plugin_args
        session = Streamlink()
        parser = MagicMock()
        plugins = parser.add_argument_group("Plugin Options")
        group = parser.add_argument_group("FunimationNow", parent=plugins)

        session.plugins = {
            'funimationnow': FunimationNow
        }

        setup_plugin_args(session, parser)
        self.assertSequenceEqual(
            group.add_argument.mock_calls,
            [
                call('--funimation-email', help=ANY),
                call('--funimation-password', help=ANY),
                call('--funimation-language', choices=["en", "ja", "english", "japanese"], default="english", help=ANY)
            ]
        )
