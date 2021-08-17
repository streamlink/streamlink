import datetime
import re
import time
import unittest
from unittest.mock import Mock, call, patch

import freezegun
import requests.cookies

from streamlink.plugin import HIGH_PRIORITY, NORMAL_PRIORITY, Plugin, pluginmatcher
from streamlink.plugin.plugin import Matcher


class TestPlugin(unittest.TestCase):
    def _create_cookie_dict(self, name, value, expires):
        return {'version': 0, 'name': name, 'value': value,
                'port': None, 'domain': "test.se", 'path': "/", 'secure': False,
                'expires': expires, 'discard': True, 'comment': None,
                'comment_url': None, 'rest': {"HttpOnly": None}, 'rfc2109': False}

    def _cookie_to_dict(self, cookie):
        r = {}
        for name in ("version", "name", "value", "port", "domain", "path",
                     "secure", "expires", "discard", "comment", "comment_url"):
            r[name] = getattr(cookie, name, None)
        r["rest"] = getattr(cookie, "rest", getattr(cookie, "_rest", None))
        return r

    def tearDown(self):
        Plugin.session = None
        Plugin.cache = None
        Plugin.module = None
        Plugin.logger = None

    def test_cookie_store_save(self):
        session = Mock()
        session.http.cookies = [
            requests.cookies.create_cookie("test-name", "test-value", domain="test.se")
        ]

        Plugin.bind(session, 'tests.test_plugin')
        Plugin.cache = Mock()
        Plugin.cache.get_all.return_value = {}

        plugin = Plugin("http://test.se")
        plugin.save_cookies(default_expires=3600)

        Plugin.cache.set.assert_called_with("__cookie:test-name:test.se:80:/",
                                            self._create_cookie_dict("test-name", "test-value", None),
                                            3600)

    def test_cookie_store_save_expires(self):
        with freezegun.freeze_time(datetime.datetime(2018, 1, 1)):
            session = Mock()
            session.http.cookies = [
                requests.cookies.create_cookie("test-name", "test-value", domain="test.se", expires=time.time() + 3600,
                                               rest={'HttpOnly': None})
            ]

            Plugin.bind(session, 'tests.test_plugin')
            Plugin.cache = Mock()
            Plugin.cache.get_all.return_value = {}

            plugin = Plugin("http://test.se")
            plugin.save_cookies(default_expires=60)

            Plugin.cache.set.assert_called_with("__cookie:test-name:test.se:80:/",
                                                self._create_cookie_dict("test-name", "test-value", 1514768400),
                                                3600)

    def test_cookie_store_load(self):
        session = Mock()
        session.http.cookies = requests.cookies.RequestsCookieJar()

        Plugin.bind(session, 'tests.test_plugin')
        Plugin.cache = Mock()
        Plugin.cache.get_all.return_value = {
            "__cookie:test-name:test.se:80:/": self._create_cookie_dict("test-name", "test-value", None)
        }
        Plugin("http://test.se")

        self.assertSequenceEqual(
            list(map(self._cookie_to_dict, session.http.cookies)),
            [self._cookie_to_dict(requests.cookies.create_cookie("test-name", "test-value", domain="test.se"))]
        )

    def test_cookie_store_clear(self):
        session = Mock()
        session.http.cookies = requests.cookies.RequestsCookieJar()

        Plugin.bind(session, 'tests.test_plugin')
        Plugin.cache = Mock()
        Plugin.cache.get_all.return_value = {
            "__cookie:test-name:test.se:80:/": self._create_cookie_dict("test-name", "test-value", None),
            "__cookie:test-name2:test.se:80:/": self._create_cookie_dict("test-name2", "test-value2", None)
        }
        plugin = Plugin("http://test.se")

        # non-empty cookiejar
        self.assertTrue(len(session.http.cookies.get_dict()) > 0)

        plugin.clear_cookies()
        self.assertSequenceEqual(
            Plugin.cache.set.mock_calls,
            [call("__cookie:test-name:test.se:80:/", None, 0),
             call("__cookie:test-name2:test.se:80:/", None, 0)])
        self.assertSequenceEqual(session.http.cookies, [])

    def test_cookie_store_clear_filter(self):
        session = Mock()
        session.http.cookies = requests.cookies.RequestsCookieJar()

        Plugin.bind(session, 'tests.test_plugin')
        Plugin.cache = Mock()
        Plugin.cache.get_all.return_value = {
            "__cookie:test-name:test.se:80:/": self._create_cookie_dict("test-name", "test-value", None),
            "__cookie:test-name2:test.se:80:/": self._create_cookie_dict("test-name2", "test-value2", None)
        }
        plugin = Plugin("http://test.se")

        # non-empty cookiejar
        self.assertTrue(len(session.http.cookies.get_dict()) > 0)

        plugin.clear_cookies(lambda c: c.name.endswith("2"))
        self.assertSequenceEqual(
            Plugin.cache.set.mock_calls,
            [call("__cookie:test-name2:test.se:80:/", None, 0)])
        self.assertSequenceEqual(
            list(map(self._cookie_to_dict, session.http.cookies)),
            [self._cookie_to_dict(requests.cookies.create_cookie("test-name", "test-value", domain="test.se"))]
        )

    def test_cookie_load_unbound(self):
        plugin = Plugin("http://test.se")
        with self.assertRaises(RuntimeError) as cm:
            plugin.load_cookies()
        self.assertEqual(str(cm.exception), "Cannot load cached cookies in unbound plugin")

    def test_cookie_save_unbound(self):
        plugin = Plugin("http://test.se")
        with self.assertRaises(RuntimeError) as cm:
            plugin.save_cookies()
        self.assertEqual(str(cm.exception), "Cannot cache cookies in unbound plugin")

    def test_cookie_clear_unbound(self):
        plugin = Plugin("http://test.se")
        with self.assertRaises(RuntimeError) as cm:
            plugin.clear_cookies()
        self.assertEqual(str(cm.exception), "Cannot clear cached cookies in unbound plugin")


class TestPluginMatcher(unittest.TestCase):
    @patch("builtins.repr", Mock(return_value="Foo"))
    def test_decorator(self):
        with self.assertRaises(TypeError) as cm:
            @pluginmatcher(re.compile(""))
            class Foo:
                pass
        self.assertEqual(str(cm.exception), "Foo is not a Plugin")

        @pluginmatcher(re.compile("foo", re.VERBOSE))
        @pluginmatcher(re.compile("bar"), priority=HIGH_PRIORITY)
        class Bar(Plugin):
            def _get_streams(self):
                pass  # pragma: no cover

        self.assertEqual(Bar.matchers, [
            Matcher(re.compile("foo", re.VERBOSE), NORMAL_PRIORITY),
            Matcher(re.compile("bar"), HIGH_PRIORITY)
        ])

    def test_url_setter(self):
        @pluginmatcher(re.compile("http://(foo)"))
        @pluginmatcher(re.compile("http://(bar)"))
        @pluginmatcher(re.compile("http://(baz)"))
        class MyPlugin(Plugin):
            def _get_streams(self):
                pass  # pragma: no cover

        MyPlugin.bind(Mock(), "tests.test_plugin")

        plugin = MyPlugin("http://foo")
        self.assertEqual(plugin.url, "http://foo")
        self.assertEqual([m is not None for m in plugin.matches], [True, False, False])
        self.assertEqual(plugin.matcher, plugin.matchers[0].pattern)
        self.assertEqual(plugin.match.group(1), "foo")

        plugin.url = "http://bar"
        self.assertEqual(plugin.url, "http://bar")
        self.assertEqual([m is not None for m in plugin.matches], [False, True, False])
        self.assertEqual(plugin.matcher, plugin.matchers[1].pattern)
        self.assertEqual(plugin.match.group(1), "bar")

        plugin.url = "http://baz"
        self.assertEqual(plugin.url, "http://baz")
        self.assertEqual([m is not None for m in plugin.matches], [False, False, True])
        self.assertEqual(plugin.matcher, plugin.matchers[2].pattern)
        self.assertEqual(plugin.match.group(1), "baz")

        plugin.url = "http://qux"
        self.assertEqual(plugin.url, "http://qux")
        self.assertEqual([m is not None for m in plugin.matches], [False, False, False])
        self.assertEqual(plugin.matcher, None)
        self.assertEqual(plugin.match, None)
