import os
import unittest

from streamlink.plugin.plugin import HIGH_PRIORITY, LOW_PRIORITY

try:
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock

from streamlink import Streamlink, NoPluginError
from streamlink.plugins import Plugin
from streamlink.stream import *


class TestSession(unittest.TestCase):
    PluginPath = os.path.join(os.path.dirname(__file__), "plugins")

    def setUp(self):
        self.session = Streamlink()
        self.session.load_plugins(self.PluginPath)

    def test_exceptions(self):
        try:
            self.session.resolve_url("invalid url")
            self.assertTrue(False)
        except NoPluginError:
            self.assertTrue(True)

    def test_load_plugins(self):
        plugins = self.session.get_plugins()
        self.assertTrue(plugins["testplugin"])

    def test_builtin_plugins(self):
        plugins = self.session.get_plugins()
        self.assertTrue("twitch" in plugins)

    def test_resolve_url(self):
        plugins = self.session.get_plugins()
        channel = self.session.resolve_url("http://test.se/channel")
        self.assertTrue(isinstance(channel, Plugin))
        self.assertTrue(isinstance(channel, plugins["testplugin"]))

    def test_resolve_url_priority(self):
        from tests.plugins.testplugin import TestPlugin

        class HighPriority(TestPlugin):
            @classmethod
            def priority(cls, url):
                return HIGH_PRIORITY

        class LowPriority(TestPlugin):
            @classmethod
            def priority(cls, url):
                return LOW_PRIORITY

        self.session.plugins = {
            "test_plugin": TestPlugin,
            "test_plugin_low": LowPriority,
            "test_plugin_high": HighPriority,
        }
        channel = self.session.resolve_url_no_redirect("http://test.se/channel")
        plugins = self.session.get_plugins()

        self.assertTrue(isinstance(channel, plugins["test_plugin_high"]))
        self.assertEqual(HIGH_PRIORITY, channel.priority(channel.url))

    def test_resolve_url_no_redirect(self):
        plugins = self.session.get_plugins()
        channel = self.session.resolve_url_no_redirect("http://test.se/channel")
        self.assertTrue(isinstance(channel, Plugin))
        self.assertTrue(isinstance(channel, plugins["testplugin"]))

    def test_options(self):
        self.session.set_option("test_option", "option")
        self.assertEqual(self.session.get_option("test_option"), "option")
        self.assertEqual(self.session.get_option("non_existing"), None)

        self.assertEqual(self.session.get_plugin_option("testplugin", "a_option"), "default")
        self.session.set_plugin_option("testplugin", "another_option", "test")
        self.assertEqual(self.session.get_plugin_option("testplugin", "another_option"), "test")
        self.assertEqual(self.session.get_plugin_option("non_existing", "non_existing"), None)
        self.assertEqual(self.session.get_plugin_option("testplugin", "non_existing"), None)

    def test_plugin(self):
        channel = self.session.resolve_url("http://test.se/channel")
        streams = channel.get_streams()

        self.assertTrue("best" in streams)
        self.assertTrue("worst" in streams)
        self.assertTrue(streams["best"] is streams["1080p"])
        self.assertTrue(streams["worst"] is streams["350k"])
        self.assertTrue(isinstance(streams["rtmp"], RTMPStream))
        self.assertTrue(isinstance(streams["http"], HTTPStream))
        self.assertTrue(isinstance(streams["hls"], HLSStream))
        self.assertTrue(isinstance(streams["akamaihd"], AkamaiHDStream))

    def test_plugin_stream_types(self):
        channel = self.session.resolve_url("http://test.se/channel")
        streams = channel.get_streams(stream_types=["http", "rtmp"])

        self.assertTrue(isinstance(streams["480p"], HTTPStream))
        self.assertTrue(isinstance(streams["480p_rtmp"], RTMPStream))

        streams = channel.get_streams(stream_types=["rtmp", "http"])

        self.assertTrue(isinstance(streams["480p"], RTMPStream))
        self.assertTrue(isinstance(streams["480p_http"], HTTPStream))

    def test_plugin_stream_sorted_excludes(self):
        channel = self.session.resolve_url("http://test.se/channel")
        streams = channel.get_streams(sorting_excludes=["1080p", "3000k"])

        self.assertTrue("best" in streams)
        self.assertTrue("worst" in streams)
        self.assertTrue(streams["best"] is streams["1500k"])

        streams = channel.get_streams(sorting_excludes=[">=1080p", ">1500k"])
        self.assertTrue(streams["best"] is streams["1500k"])

        streams = channel.get_streams(sorting_excludes=lambda q: not q.endswith("p"))
        self.assertTrue(streams["best"] is streams["3000k"])

    def test_plugin_support(self):
        channel = self.session.resolve_url("http://test.se/channel")
        streams = channel.get_streams()

        self.assertTrue("support" in streams)
        self.assertTrue(isinstance(streams["support"], HTTPStream))


if __name__ == "__main__":
    unittest.main()
