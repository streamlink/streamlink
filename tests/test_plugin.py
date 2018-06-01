import unittest
import time
import datetime
import freezegun
import requests.cookies


from tests.mock import Mock, ANY, call
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
        with freezegun.freeze_time(lambda: datetime.datetime(2018, 1, 1)):
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
        plugin = Plugin("http://test.se")
        #plugin.load_cookies()
        self.assertSequenceEqual(
            list(map(self._cookie_to_dict, session.http.cookies)),
            [self._cookie_to_dict(requests.cookies.create_cookie("test-name", "test-value", domain="test.se"))]
        )

    def test_cookie_store_clear(self):
        self.maxDiff = None
        session = Mock()
        session.http.cookies = requests.cookies.RequestsCookieJar()

        Plugin.bind(session, 'tests.test_plugin')
        Plugin.cache = Mock()
        Plugin.cache.get_all.return_value = {
            "__cookie:test-name:test.se:80:/": self._create_cookie_dict("test-name", "test-value", None),
            "__cookie:test-name2:test.se:80:/": self._create_cookie_dict("test-name2", "test-value2", None)
        }
        plugin = Plugin("http://test.se")
        #plugin.load_cookies()
        print(list(session.http.cookies))
        # non-empty cookiejar
        self.assertTrue(len(session.http.cookies.get_dict()) > 0)


        plugin.clear_cookies()
        self.assertSequenceEqual(
            Plugin.cache.set.mock_calls,
            [call("__cookie:test-name:test.se:80:/", None, 0),
             call("__cookie:test-name2:test.se:80:/", None, 0)])
        self.assertSequenceEqual(session.http.cookies, [])
