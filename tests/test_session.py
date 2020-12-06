import os
import unittest
from unittest.mock import call, patch

from streamlink import NoPluginError, Streamlink
from streamlink.plugin.plugin import HIGH_PRIORITY, LOW_PRIORITY
from streamlink.plugins import Plugin
from streamlink.stream import AkamaiHDStream, HLSStream, HTTPStream, RTMPStream


class TestSession(unittest.TestCase):
    plugin_path = os.path.join(os.path.dirname(__file__), "plugin")

    def subject(self, load_plugins=True):
        session = Streamlink()
        if load_plugins:
            session.load_plugins(self.plugin_path)

        return session

    def test_exceptions(self):
        session = self.subject()
        self.assertRaises(NoPluginError, session.resolve_url, "invalid url", follow_redirect=False)

    def test_load_plugins(self):
        session = self.subject()
        plugins = session.get_plugins()
        self.assertIn("testplugin", plugins)
        self.assertNotIn("testplugin_missing", plugins)
        self.assertNotIn("testplugin_invalid", plugins)

    def test_load_plugins_builtin(self):
        session = self.subject()
        plugins = session.get_plugins()
        self.assertIn("twitch", plugins)
        self.assertEqual(plugins["twitch"].__module__, "streamlink.plugins.twitch")

    @patch("streamlink.session.log")
    def test_load_plugins_override(self, mock_log):
        session = self.subject()
        plugins = session.get_plugins()
        file = os.path.join(os.path.dirname(__file__), "plugin", "testplugin_override.py")
        self.assertIn("testplugin", plugins)
        self.assertNotIn("testplugin_override", plugins)
        self.assertEqual(plugins["testplugin"].__name__, "TestPluginOverride")
        self.assertEqual(plugins["testplugin"].__module__, "streamlink.plugins.testplugin_override")
        self.assertEqual(mock_log.debug.mock_calls, [call(f"Plugin testplugin is being overridden by {file}")])

    @patch("streamlink.session.load_module")
    @patch("streamlink.session.log")
    def test_load_plugins_importerror(self, mock_log, mock_load_module):
        mock_load_module.side_effect = ImportError()
        session = self.subject()
        plugins = session.get_plugins()
        self.assertGreater(len(mock_log.exception.mock_calls), 0)
        self.assertEqual(len(plugins.keys()), 0)

    @patch("streamlink.session.load_module")
    @patch("streamlink.session.log")
    def test_load_plugins_syntaxerror(self, mock_log, mock_load_module):
        mock_load_module.side_effect = SyntaxError()
        with self.assertRaises(SyntaxError):
            self.subject()

    def test_resolve_url(self):
        session = self.subject()
        plugins = session.get_plugins()
        plugin = session.resolve_url("http://test.se/channel")
        self.assertTrue(isinstance(plugin, Plugin))
        self.assertTrue(isinstance(plugin, plugins["testplugin"]))

    def test_resolve_url_priority(self):
        from tests.plugin.testplugin import TestPlugin

        class HighPriority(TestPlugin):
            @classmethod
            def priority(cls, url):
                return HIGH_PRIORITY

        class LowPriority(TestPlugin):
            @classmethod
            def priority(cls, url):
                return LOW_PRIORITY

        session = self.subject(load_plugins=False)
        session.plugins = {
            "test_plugin": TestPlugin,
            "test_plugin_low": LowPriority,
            "test_plugin_high": HighPriority,
        }
        plugin = session.resolve_url_no_redirect("http://test.se/channel")
        plugins = session.get_plugins()

        self.assertTrue(isinstance(plugin, plugins["test_plugin_high"]))
        self.assertEqual(HIGH_PRIORITY, plugin.priority(plugin.url))

    def test_resolve_url_no_redirect(self):
        session = self.subject()
        plugin = session.resolve_url_no_redirect("http://test.se/channel")
        plugins = session.get_plugins()
        self.assertTrue(isinstance(plugin, Plugin))
        self.assertTrue(isinstance(plugin, plugins["testplugin"]))

    def test_options(self):
        session = self.subject()
        session.set_option("test_option", "option")
        self.assertEqual(session.get_option("test_option"), "option")
        self.assertEqual(session.get_option("non_existing"), None)

        self.assertEqual(session.get_plugin_option("testplugin", "a_option"), "default")
        session.set_plugin_option("testplugin", "another_option", "test")
        self.assertEqual(session.get_plugin_option("testplugin", "another_option"), "test")
        self.assertEqual(session.get_plugin_option("non_existing", "non_existing"), None)
        self.assertEqual(session.get_plugin_option("testplugin", "non_existing"), None)

    def test_plugin(self):
        session = self.subject()
        plugin = session.resolve_url("http://test.se/channel")
        streams = plugin.streams()

        self.assertTrue("best" in streams)
        self.assertTrue("worst" in streams)
        self.assertTrue(streams["best"] is streams["1080p"])
        self.assertTrue(streams["worst"] is streams["350k"])
        self.assertTrue(isinstance(streams["rtmp"], RTMPStream))
        self.assertTrue(isinstance(streams["http"], HTTPStream))
        self.assertTrue(isinstance(streams["hls"], HLSStream))
        self.assertTrue(isinstance(streams["akamaihd"], AkamaiHDStream))

    def test_plugin_stream_types(self):
        session = self.subject()
        plugin = session.resolve_url("http://test.se/channel")
        streams = plugin.streams(stream_types=["http", "rtmp"])

        self.assertTrue(isinstance(streams["480p"], HTTPStream))
        self.assertTrue(isinstance(streams["480p_rtmp"], RTMPStream))

        streams = plugin.streams(stream_types=["rtmp", "http"])

        self.assertTrue(isinstance(streams["480p"], RTMPStream))
        self.assertTrue(isinstance(streams["480p_http"], HTTPStream))

    def test_plugin_stream_sorting_excludes(self):
        session = self.subject()
        plugin = session.resolve_url("http://test.se/channel")

        streams = plugin.streams(sorting_excludes=[])
        self.assertTrue("best" in streams)
        self.assertTrue("worst" in streams)
        self.assertFalse("best-unfiltered" in streams)
        self.assertFalse("worst-unfiltered" in streams)
        self.assertTrue(streams["worst"] is streams["350k"])
        self.assertTrue(streams["best"] is streams["1080p"])

        streams = plugin.streams(sorting_excludes=["1080p", "3000k"])
        self.assertTrue("best" in streams)
        self.assertTrue("worst" in streams)
        self.assertFalse("best-unfiltered" in streams)
        self.assertFalse("worst-unfiltered" in streams)
        self.assertTrue(streams["worst"] is streams["350k"])
        self.assertTrue(streams["best"] is streams["1500k"])

        streams = plugin.streams(sorting_excludes=[">=1080p", ">1500k"])
        self.assertTrue(streams["best"] is streams["1500k"])

        streams = plugin.streams(sorting_excludes=lambda q: not q.endswith("p"))
        self.assertTrue(streams["best"] is streams["3000k"])

        streams = plugin.streams(sorting_excludes=lambda q: False)
        self.assertFalse("best" in streams)
        self.assertFalse("worst" in streams)
        self.assertTrue("best-unfiltered" in streams)
        self.assertTrue("worst-unfiltered" in streams)
        self.assertTrue(streams["worst-unfiltered"] is streams["350k"])
        self.assertTrue(streams["best-unfiltered"] is streams["1080p"])

        plugin = session.resolve_url("http://test.se/UnsortableStreamNames")
        streams = plugin.streams()
        self.assertFalse("best" in streams)
        self.assertFalse("worst" in streams)
        self.assertFalse("best-unfiltered" in streams)
        self.assertFalse("worst-unfiltered" in streams)
        self.assertTrue("vod" in streams)
        self.assertTrue("vod_alt" in streams)
        self.assertTrue("vod_alt2" in streams)

    def test_set_and_get_locale(self):
        session = Streamlink()
        session.set_option("locale", "en_US")
        self.assertEqual(session.localization.country.alpha2, "US")
        self.assertEqual(session.localization.language.alpha2, "en")
        self.assertEqual(session.localization.language_code, "en_US")

    def test_https_proxy_default(self):
        session = self.subject(load_plugins=False)
        session.set_option("http-proxy", "http://testproxy.com")

        self.assertEqual("http://testproxy.com", session.http.proxies['http'])
        self.assertEqual("http://testproxy.com", session.http.proxies['https'])

    def test_https_proxy_set_first(self):
        session = self.subject(load_plugins=False)
        session.set_option("https-proxy", "https://testhttpsproxy.com")
        session.set_option("http-proxy", "http://testproxy.com")

        self.assertEqual("http://testproxy.com", session.http.proxies['http'])
        self.assertEqual("https://testhttpsproxy.com", session.http.proxies['https'])

    def test_https_proxy_default_override(self):
        session = self.subject(load_plugins=False)
        session.set_option("http-proxy", "http://testproxy.com")
        session.set_option("https-proxy", "https://testhttpsproxy.com")

        self.assertEqual("http://testproxy.com", session.http.proxies['http'])
        self.assertEqual("https://testhttpsproxy.com", session.http.proxies['https'])

    def test_https_proxy_set_only(self):
        session = self.subject(load_plugins=False)
        session.set_option("https-proxy", "https://testhttpsproxy.com")

        self.assertFalse("http" in session.http.proxies)
        self.assertEqual("https://testhttpsproxy.com", session.http.proxies['https'])
