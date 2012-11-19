import os
import unittest

from livestreamer import Livestreamer, PluginError, NoPluginError
from livestreamer.plugins import Plugin
from livestreamer.stream import *


class TestSession(unittest.TestCase):
    PluginPath = os.path.join(os.path.dirname(__file__), "plugins")

    def setUp(self):
        self.session = Livestreamer()
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
        self.assertTrue("justintv" in plugins)

    def test_resolve_url(self):
        plugins = self.session.get_plugins()
        channel = self.session.resolve_url("http://test.se/channel")
        self.assertIsInstance(channel, Plugin)
        self.assertIsInstance(channel, plugins["testplugin"])

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
        self.assertIs(streams["best"], streams["1080p"])
        self.assertIsInstance(streams["rtmp"], RTMPStream)
        self.assertIsInstance(streams["http"], HTTPStream)
        self.assertIsInstance(streams["hls"], HLSStream)
        self.assertIsInstance(streams["akamaihd"], AkamaiHDStream)

if __name__ == "__main__":
    unittest.main()
