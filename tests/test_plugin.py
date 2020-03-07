import unittest
import time
import datetime
import freezegun
import requests.cookies


from tests.mock import Mock, call
from streamlink.plugin import Plugin


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
        self.assertRaises(RuntimeError, plugin.load_cookies)

    def test_cookie_save_unbound(self):
        plugin = Plugin("http://test.se")
        self.assertRaises(RuntimeError, plugin.save_cookies)

    def test_cookie_clear_unbound(self):
        plugin = Plugin("http://test.se")
        self.assertRaises(RuntimeError, plugin.clear_cookies)
