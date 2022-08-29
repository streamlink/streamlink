import logging
import re
import time
import unittest
from typing import Type
from unittest.mock import Mock, call, patch

import freezegun
import pytest
import requests.cookies

from streamlink.plugin import (
    HIGH_PRIORITY,
    NORMAL_PRIORITY,
    Plugin,
    PluginArgument,
    PluginArguments,
    pluginargument,
    pluginmatcher,
)
# noinspection PyProtectedMember
from streamlink.plugin.plugin import Matcher, _COOKIE_KEYS
from streamlink.session import Streamlink


class FakePlugin(Plugin):
    def _get_streams(self):
        pass  # pragma: no cover


class RenamedPlugin(FakePlugin):
    __module__ = "foo.bar.baz"


class CustomConstructorOnePlugin(FakePlugin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class CustomConstructorTwoPlugin(FakePlugin):
    def __init__(self, session, url):
        super().__init__(session, url)


class DeprecatedPlugin(FakePlugin):
    def __init__(self, url):
        super().__init__(url)  # type: ignore[call-arg]
        self.custom_attribute = url.upper()


class TestPlugin:
    @pytest.mark.parametrize("pluginclass,module,logger", [
        (Plugin, "plugin", "streamlink.plugin.plugin"),
        (FakePlugin, "test_plugin", "tests.test_plugin"),
        (RenamedPlugin, "baz", "foo.bar.baz"),
        (CustomConstructorOnePlugin, "test_plugin", "tests.test_plugin"),
        (CustomConstructorTwoPlugin, "test_plugin", "tests.test_plugin"),
    ])
    def test_constructor(self, caplog: pytest.LogCaptureFixture, pluginclass: Type[Plugin], module: str, logger: str):
        session = Mock()
        with patch("streamlink.plugin.plugin.Cache") as mock_cache, \
             patch.object(pluginclass, "load_cookies") as mock_load_cookies:
            plugin = pluginclass(session, "http://localhost")

        assert not caplog.records

        assert plugin.session is session
        assert plugin.url == "http://localhost"

        assert plugin.module == module

        assert isinstance(plugin.logger, logging.Logger)
        assert plugin.logger.name == logger

        assert mock_cache.call_args_list == [call(filename="plugin-cache.json", key_prefix=module)]
        assert plugin.cache == mock_cache()

        assert mock_load_cookies.call_args_list == [call()]

    def test_constructor_wrapper(self, caplog: pytest.LogCaptureFixture):
        session = Mock()
        with patch("streamlink.plugin.plugin.Cache") as mock_cache, \
             patch.object(DeprecatedPlugin, "load_cookies") as mock_load_cookies:
            plugin = DeprecatedPlugin(session, "http://localhost")  # type: ignore[call-arg]

        assert isinstance(plugin, DeprecatedPlugin)
        assert plugin.custom_attribute == "HTTP://LOCALHOST"
        assert [(record.levelname, record.message) for record in caplog.records] == [
            ("warning", "Initialized test_plugin plugin with deprecated constructor"),
        ]

        assert plugin.session is session
        assert plugin.url == "http://localhost"

        assert plugin.module == "test_plugin"

        assert isinstance(plugin.logger, logging.Logger)
        assert plugin.logger.name == "tests.test_plugin"

        assert mock_cache.call_args_list == [call(filename="plugin-cache.json", key_prefix="test_plugin")]
        assert plugin.cache == mock_cache()

        assert mock_load_cookies.call_args_list == [call()]


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
        class Bar(FakePlugin):
            pass

        self.assertEqual(Bar.matchers, [
            Matcher(re.compile("foo", re.VERBOSE), NORMAL_PRIORITY),
            Matcher(re.compile("bar"), HIGH_PRIORITY)
        ])

    def test_url_setter(self):
        @pluginmatcher(re.compile("http://(foo)"))
        @pluginmatcher(re.compile("http://(bar)"))
        @pluginmatcher(re.compile("http://(baz)"))
        class MyPlugin(FakePlugin):
            pass

        plugin = MyPlugin(Mock(), "http://foo")
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


class TestPluginArguments:
    @pluginargument("foo", dest="_foo", help="FOO")
    @pluginargument("bar", dest="_bar", help="BAR")
    @pluginargument("baz", dest="_baz", help="BAZ")
    class DecoratedPlugin(FakePlugin):
        pass

    class ClassAttrPlugin(FakePlugin):
        arguments = PluginArguments(
            PluginArgument("foo", dest="_foo", help="FOO"),
            PluginArgument("bar", dest="_bar", help="BAR"),
            PluginArgument("baz", dest="_baz", help="BAZ"),
        )

    @pytest.mark.parametrize("pluginclass", [DecoratedPlugin, ClassAttrPlugin])
    def test_arguments(self, pluginclass):
        assert pluginclass.arguments is not None
        assert tuple(arg.name for arg in pluginclass.arguments) == ("foo", "bar", "baz"), "Argument name"
        assert tuple(arg.dest for arg in pluginclass.arguments) == ("_foo", "_bar", "_baz"), "Argument keyword"
        assert tuple(arg.options.get("help") for arg in pluginclass.arguments) == ("FOO", "BAR", "BAZ"), "argparse keyword"

    def test_mixed(self):
        @pluginargument("qux")
        class MixedPlugin(self.ClassAttrPlugin):
            pass

        assert tuple(arg.name for arg in MixedPlugin.arguments) == ("qux", "foo", "bar", "baz")

    def test_decorator_typerror(self):
        with pytest.raises(TypeError) as cm:
            with patch("builtins.repr", Mock(side_effect=lambda obj: obj.__name__)):
                @pluginargument("foo")
                class Foo:
                    pass
        assert str(cm.value) == "Foo is not a Plugin"

    def test_empty(self):
        assert Plugin.arguments is None


@pytest.mark.parametrize("attr", ["id", "author", "category", "title"])
def test_plugin_metadata(attr):
    plugin = FakePlugin(Mock(), "https://foo.bar/")
    getter = getattr(plugin, f"get_{attr}")
    assert callable(getter)

    assert getattr(plugin, attr) is None
    assert getter() is None

    setattr(plugin, attr, " foo bar ")
    assert getter() == "foo bar"

    class Foo:
        def __str__(self):
            return " baz qux "

    setattr(plugin, attr, Foo())
    assert getter() == "baz qux"


# TODO: python 3.7 removal: move this as static method to the TestCookies class
def _create_cookie_dict(name, value, expires=None):
    return dict(
        version=0,
        name=name,
        value=value,
        port=None,
        domain="test.se",
        path="/",
        secure=False,
        expires=expires,
        discard=True,
        comment=None,
        comment_url=None,
        rest={"HttpOnly": None},
        rfc2109=False,
    )


class TestCookies:
    @pytest.fixture
    def session(self):
        return Streamlink()

    @pytest.fixture
    def pluginclass(self):
        class MyPlugin(FakePlugin):
            __module__ = "myplugin"

        return MyPlugin

    @pytest.fixture
    def plugincache(self, request):
        with patch("streamlink.plugin.plugin.Cache") as mock_cache:
            cache = mock_cache("plugin-cache.json", "myplugin")
            cache.get_all.return_value = request.param
            yield cache

    @pytest.fixture
    def logger(self, pluginclass: Type[Plugin]):
        with patch("streamlink.plugin.plugin.logging") as mock_logging:
            yield mock_logging.getLogger(pluginclass.__module__)

    @pytest.fixture
    def plugin(self, pluginclass: Type[Plugin], session: Streamlink, plugincache: Mock, logger: Mock):
        plugin = pluginclass(session, "http://test.se")
        assert plugin.cache is plugincache
        assert plugin.logger is logger
        yield plugin

    @staticmethod
    def _cookie_to_dict(cookie):
        r = {name: getattr(cookie, name, None) for name in _COOKIE_KEYS}
        r["rest"] = getattr(cookie, "rest", getattr(cookie, "_rest", None))
        return r

    def _cookies_to_list(self, cookies):
        return list(self._cookie_to_dict(cookie) for cookie in cookies)

    @pytest.mark.parametrize(
        "plugincache",
        [{
            "__cookie:test-name1:test.se:80:/": _create_cookie_dict("test-name1", "test-value1"),
            "__cookie:test-name2:test.se:80:/": _create_cookie_dict("test-name2", "test-value2"),
            "unrelated": "data",
        }],
        indirect=True,
    )
    def test_load(self, session: Streamlink, plugin: Plugin, plugincache: Mock, logger: Mock):
        assert self._cookies_to_list(session.http.cookies) == self._cookies_to_list([
            requests.cookies.create_cookie("test-name1", "test-value1", domain="test.se"),
            requests.cookies.create_cookie("test-name2", "test-value2", domain="test.se"),
        ])
        assert logger.debug.call_args_list == [call("Restored cookies: test-name1, test-name2")]

    @pytest.mark.parametrize("plugincache", [{}], indirect=True)
    def test_save(self, session: Streamlink, plugin: Plugin, plugincache: Mock, logger: Mock):
        cookie1 = requests.cookies.create_cookie("test-name1", "test-value1", domain="test.se")
        cookie2 = requests.cookies.create_cookie("test-name2", "test-value2", domain="test.se")
        session.http.cookies.set_cookie(cookie1)
        session.http.cookies.set_cookie(cookie2)

        plugin.save_cookies(lambda cookie: cookie.name == "test-name1", default_expires=3600)
        assert plugincache.set.call_args_list == [call(
            "__cookie:test-name1:test.se:80:/",
            _create_cookie_dict("test-name1", "test-value1", None),
            3600,
        )]
        assert logger.debug.call_args_list == [call("Saved cookies: test-name1")]

    @freezegun.freeze_time("1970-01-01T00:00:00Z")
    @pytest.mark.parametrize("plugincache", [{}], indirect=True)
    def test_save_expires(self, session: Streamlink, plugin: Plugin, plugincache: Mock):
        cookie = requests.cookies.create_cookie(
            "test-name",
            "test-value",
            domain="test.se",
            expires=time.time() + 3600,
            rest={"HttpOnly": None},
        )
        session.http.cookies.set_cookie(cookie)

        plugin.save_cookies(default_expires=60)
        assert plugincache.set.call_args_list == [call(
            "__cookie:test-name:test.se:80:/",
            _create_cookie_dict("test-name", "test-value", 3600),
            3600,
        )]

    @pytest.mark.parametrize(
        "plugincache",
        [{
            "__cookie:test-name1:test.se:80:/": _create_cookie_dict("test-name1", "test-value1", None),
            "__cookie:test-name2:test.se:80:/": _create_cookie_dict("test-name2", "test-value2", None),
            "unrelated": "data",
        }],
        indirect=True,
    )
    def test_clear(self, session: Streamlink, plugin: Plugin, plugincache: Mock):
        assert tuple(session.http.cookies.keys()) == ("test-name1", "test-name2")

        plugin.clear_cookies()
        assert call("__cookie:test-name1:test.se:80:/", None, 0) in plugincache.set.call_args_list
        assert call("__cookie:test-name2:test.se:80:/", None, 0) in plugincache.set.call_args_list
        assert len(session.http.cookies.keys()) == 0

    @pytest.mark.parametrize(
        "plugincache",
        [{
            "__cookie:test-name1:test.se:80:/": _create_cookie_dict("test-name1", "test-value1", None),
            "__cookie:test-name2:test.se:80:/": _create_cookie_dict("test-name2", "test-value2", None),
            "unrelated": "data",
        }],
        indirect=True,
    )
    def test_clear_filter(self, session: Streamlink, plugin: Plugin, plugincache: Mock):
        assert tuple(session.http.cookies.keys()) == ("test-name1", "test-name2")

        plugin.clear_cookies(lambda cookie: cookie.name == "test-name2")
        assert call("__cookie:test-name1:test.se:80:/", None, 0) not in plugincache.set.call_args_list
        assert call("__cookie:test-name2:test.se:80:/", None, 0) in plugincache.set.call_args_list
        assert tuple(session.http.cookies.keys()) == ("test-name1",)
