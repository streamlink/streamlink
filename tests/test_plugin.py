import logging
import re
import time
from operator import eq, gt, lt
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
from streamlink.plugin.plugin import _COOKIE_KEYS, Matcher, parse_params, stream_weight
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
    @pytest.mark.parametrize(("pluginclass", "module", "logger"), [
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

    def test_constructor_wrapper(self, recwarn: pytest.WarningsRecorder):
        session = Mock()
        with patch("streamlink.plugin.plugin.Cache") as mock_cache, \
             patch.object(DeprecatedPlugin, "load_cookies") as mock_load_cookies:
            plugin = DeprecatedPlugin(session, "http://localhost")  # type: ignore[call-arg]

        assert isinstance(plugin, DeprecatedPlugin)
        assert plugin.custom_attribute == "HTTP://LOCALHOST"
        assert [(record.category, str(record.message), record.filename) for record in recwarn.list] == [
            (
                FutureWarning,
                "Initialized test_plugin plugin with deprecated constructor",
                __file__,
            ),
        ]

        assert plugin.session is session
        assert plugin.url == "http://localhost"

        assert plugin.module == "test_plugin"

        assert isinstance(plugin.logger, logging.Logger)
        assert plugin.logger.name == "tests.test_plugin"

        assert mock_cache.call_args_list == [call(filename="plugin-cache.json", key_prefix="test_plugin")]
        assert plugin.cache == mock_cache()

        assert mock_load_cookies.call_args_list == [call()]


class TestPluginMatcher:
    # noinspection PyUnusedLocal
    def test_decorator(self):
        with pytest.raises(TypeError) as cm:
            @pluginmatcher(re.compile(""))
            class MyPlugin:
                pass
        assert str(cm.value) == "MyPlugin is not a Plugin"

    # noinspection PyUnusedLocal
    def test_named_duplicate(self):
        with pytest.raises(ValueError, match=r"^A matcher named 'foo' has already been registered$"):
            @pluginmatcher(re.compile("http://foo"), name="foo")
            @pluginmatcher(re.compile("http://foo"), name="foo")
            class MyPlugin(FakePlugin):
                pass

    def test_no_matchers(self):
        class MyPlugin(FakePlugin):
            pass

        plugin = MyPlugin(Mock(), "http://foo")
        assert plugin.url == "http://foo"
        assert plugin.matchers is None
        assert plugin.matches == []
        assert plugin.matcher is None
        assert plugin.match is None

    def test_matchers(self):
        @pluginmatcher(re.compile("foo", re.VERBOSE))
        @pluginmatcher(re.compile("bar"), priority=HIGH_PRIORITY)
        @pluginmatcher(re.compile("baz"), priority=HIGH_PRIORITY, name="baz")
        class MyPlugin(FakePlugin):
            pass

        assert MyPlugin.matchers == [
            Matcher(re.compile("foo", re.VERBOSE), NORMAL_PRIORITY),
            Matcher(re.compile("bar"), HIGH_PRIORITY),
            Matcher(re.compile("baz"), HIGH_PRIORITY, "baz"),
        ]

    def test_url_setter(self):
        @pluginmatcher(re.compile("http://(foo)"))
        @pluginmatcher(re.compile("http://(bar)"))
        @pluginmatcher(re.compile("http://(baz)"))
        class MyPlugin(FakePlugin):
            pass

        plugin = MyPlugin(Mock(), "http://foo")
        assert plugin.url == "http://foo"
        assert [m is not None for m in plugin.matches] == [True, False, False]
        assert plugin.matcher is plugin.matchers[0].pattern
        assert plugin.match.group(1) == "foo"

        plugin.url = "http://bar"
        assert plugin.url == "http://bar"
        assert [m is not None for m in plugin.matches] == [False, True, False]
        assert plugin.matcher is plugin.matchers[1].pattern
        assert plugin.match.group(1) == "bar"

        plugin.url = "http://baz"
        assert plugin.url == "http://baz"
        assert [m is not None for m in plugin.matches] == [False, False, True]
        assert plugin.matcher is plugin.matchers[2].pattern
        assert plugin.match.group(1) == "baz"

        plugin.url = "http://qux"
        assert plugin.url == "http://qux"
        assert [m is not None for m in plugin.matches] == [False, False, False]
        assert plugin.matcher is None
        assert plugin.match is None

    def test_named_matchers_and_matches(self):
        @pluginmatcher(re.compile("http://foo"), name="foo")
        @pluginmatcher(re.compile("http://bar"), name="bar")
        class MyPlugin(FakePlugin):
            pass

        plugin = MyPlugin(Mock(), "http://foo")

        assert plugin.matchers["foo"] is plugin.matchers[0]
        assert plugin.matchers["bar"] is plugin.matchers[1]
        with pytest.raises(IndexError):
            plugin.matchers.__getitem__(2)
        with pytest.raises(KeyError):
            plugin.matchers.__getitem__("baz")

        assert plugin.matches["foo"] is plugin.matches[0]
        assert plugin.matches["bar"] is plugin.matches[1]
        assert plugin.matches["foo"] is not None
        assert plugin.matches["bar"] is None
        with pytest.raises(IndexError):
            plugin.matches.__getitem__(2)
        with pytest.raises(KeyError):
            plugin.matches.__getitem__("baz")

        plugin.url = "http://bar"
        assert plugin.matches["foo"] is None
        assert plugin.matches["bar"] is not None

        plugin.url = "http://baz"
        assert plugin.matches["foo"] is None
        assert plugin.matches["bar"] is None


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
        with patch("builtins.repr", Mock(side_effect=lambda obj: obj.__name__)):
            with pytest.raises(TypeError) as cm:
                # noinspection PyUnusedLocal
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


class TestCookies:
    @staticmethod
    def create_cookie_dict(name, value, expires=None):
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

    # TODO: py39 support end: remove explicit dummy context binding of static method
    _create_cookie_dict = create_cookie_dict.__get__(object)

    @pytest.fixture()
    def pluginclass(self):
        class MyPlugin(FakePlugin):
            __module__ = "myplugin"

        return MyPlugin

    @pytest.fixture()
    def plugincache(self, request):
        with patch("streamlink.plugin.plugin.Cache") as mock_cache:
            cache = mock_cache("plugin-cache.json", "myplugin")
            cache.get_all.return_value = request.param
            yield cache

    @pytest.fixture()
    def logger(self, pluginclass: Type[Plugin]):
        with patch("streamlink.plugin.plugin.logging") as mock_logging:
            yield mock_logging.getLogger(pluginclass.__module__)

    @pytest.fixture()
    def plugin(self, pluginclass: Type[Plugin], session: Streamlink, plugincache: Mock, logger: Mock):
        plugin = pluginclass(session, "http://test.se")
        assert plugin.cache is plugincache
        assert plugin.logger is logger
        return plugin

    @staticmethod
    def _cookie_to_dict(cookie):
        r = {name: getattr(cookie, name, None) for name in _COOKIE_KEYS}
        r["rest"] = getattr(cookie, "rest", getattr(cookie, "_rest", None))
        return r

    def _cookies_to_list(self, cookies):
        return [self._cookie_to_dict(cookie) for cookie in cookies]

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
            self.create_cookie_dict("test-name1", "test-value1", None),
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
            self.create_cookie_dict("test-name", "test-value", 3600),
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


@pytest.mark.parametrize(("params", "expected"), [
    (
        None,
        {},
    ),
    (
        "foo=bar",
        dict(foo="bar"),
    ),
    (
        "verify=False",
        dict(verify=False),
    ),
    (
        "timeout=123.45",
        dict(timeout=123.45),
    ),
    (
        "verify=False params={'key': 'a value'}",
        dict(verify=False, params=dict(key="a value")),
    ),
    (
        "\"conn=['B:1', 'S:authMe', 'O:1', 'NN:code:1.23', 'NS:flag:ok', 'O:0']",
        dict(conn=["B:1", "S:authMe", "O:1", "NN:code:1.23", "NS:flag:ok", "O:0"]),
    ),
])
def test_parse_params(params, expected):
    assert parse_params(params) == expected


@pytest.mark.parametrize(("weight", "expected"), [
    ("720p", (720, "pixels")),
    ("720p+", (721, "pixels")),
    ("720p60", (780, "pixels")),
])
def test_stream_weight_value(weight, expected):
    assert stream_weight(weight) == expected


@pytest.mark.parametrize(("weight_a", "operator", "weight_b"), [
    ("720p+", gt, "720p"),
    ("720p_3000k", gt, "720p_2500k"),
    ("720p60_3000k", gt, "720p_3000k"),
    ("3000k", gt, "2500k"),
    ("720p", eq, "720p"),
    ("720p_3000k", lt, "720p+_3000k"),
    # with audio
    ("720p+a256k", gt, "720p+a128k"),
    ("720p+a256k", gt, "360p+a256k"),
    ("720p+a128k", gt, "360p+a256k"),
])
def test_stream_weight(weight_a, weight_b, operator):
    assert operator(stream_weight(weight_a), stream_weight(weight_b))
