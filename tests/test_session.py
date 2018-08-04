import unittest
import os

from streamlink import Streamlink, NoPluginError
from streamlink.plugin.plugin import HIGH_PRIORITY, LOW_PRIORITY
from streamlink.plugins import Plugin
from streamlink.session import print_small_exception
from streamlink.stream import AkamaiHDStream, HLSStream, HTTPStream, RTMPStream
from tests.mock import patch, call


class TestSession(unittest.TestCase):
    PluginPath = os.path.join(os.path.dirname(__file__), "plugins")

    def setUp(self):
        self.session = Streamlink()
        self.session.load_plugins(self.PluginPath)

    def test_exceptions(self):
        self.assertRaises(NoPluginError, self.session.resolve_url, "invalid url", follow_redirect=False)

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
        streams = channel.streams()

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
        streams = channel.streams(stream_types=["http", "rtmp"])

        self.assertTrue(isinstance(streams["480p"], HTTPStream))
        self.assertTrue(isinstance(streams["480p_rtmp"], RTMPStream))

        streams = channel.streams(stream_types=["rtmp", "http"])

        self.assertTrue(isinstance(streams["480p"], RTMPStream))
        self.assertTrue(isinstance(streams["480p_http"], HTTPStream))

    def test_plugin_stream_sorted_excludes(self):
        channel = self.session.resolve_url("http://test.se/channel")
        streams = channel.streams(sorting_excludes=["1080p", "3000k"])

        self.assertTrue("best" in streams)
        self.assertTrue("worst" in streams)
        self.assertTrue(streams["best"] is streams["1500k"])

        streams = channel.streams(sorting_excludes=[">=1080p", ">1500k"])
        self.assertTrue(streams["best"] is streams["1500k"])

        streams = channel.streams(sorting_excludes=lambda q: not q.endswith("p"))
        self.assertTrue(streams["best"] is streams["3000k"])

    def test_plugin_support(self):
        channel = self.session.resolve_url("http://test.se/channel")
        streams = channel.streams()

        self.assertTrue("support" in streams)
        self.assertTrue(isinstance(streams["support"], HTTPStream))

    @patch("streamlink.session.sys.stderr")
    def test_short_exception(self, stderr):
        try:
            raise RuntimeError("test exception")
        except RuntimeError:
            print_small_exception("test_short_exception")
            self.assertSequenceEqual(
                [call('RuntimeError: test exception\n'), call('\n')],
                stderr.write.mock_calls)

    def test_set_and_get_locale(self):
        session = Streamlink()
        session.set_option("locale", "en_US")
        self.assertEqual(session.localization.country.alpha2, "US")
        self.assertEqual(session.localization.language.alpha2, "en")
        self.assertEqual(session.localization.language_code, "en_US")


if __name__ == "__main__":
    unittest.main()
