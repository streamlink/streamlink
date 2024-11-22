from __future__ import annotations

import argparse
import logging
import re
import time
from contextlib import nullcontext
from operator import eq, gt, lt
from typing import Any
from unittest.mock import Mock, call, patch

import freezegun
import pytest
import requests.cookies

from streamlink.options import Options
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
from streamlink.plugin.plugin import (
    _COOKIE_KEYS,  # noqa: PLC2701
    _PLUGINARGUMENT_TYPE_REGISTRY,  # noqa: PLC2701
    Matcher,
    parse_params,
    stream_weight,
)
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


class TestPlugin:
    @pytest.mark.parametrize(
        ("pluginclass", "module", "logger"),
        [
            (Plugin, "plugin", "streamlink.plugin.plugin"),
            (FakePlugin, "test_plugin", "tests.test_plugin"),
            (RenamedPlugin, "baz", "foo.bar.baz"),
            (CustomConstructorOnePlugin, "test_plugin", "tests.test_plugin"),
            (CustomConstructorTwoPlugin, "test_plugin", "tests.test_plugin"),
        ],
    )
    def test_constructor(self, caplog: pytest.LogCaptureFixture, pluginclass: type[Plugin], module: str, logger: str):
        session = Mock()
        with (
            patch("streamlink.plugin.plugin.Cache") as mock_cache,
            patch.object(pluginclass, "load_cookies") as mock_load_cookies,
        ):
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

    def test_constructor_options(self):
        one = FakePlugin(Mock(), "https://mocked", Options({"key": "val"}))
        two = FakePlugin(Mock(), "https://mocked")
        assert one.get_option("key") == "val"
        assert two.get_option("key") is None

        one.set_option("key", "other")
        assert one.get_option("key") == "other"
        assert two.get_option("key") is None


class TestPluginMatcher:
    # noinspection PyUnusedLocal
    def test_decorator(self):
        class MyPlugin:
            pass

        with pytest.raises(TypeError) as cm:
            # noinspection PyTypeChecker
            pluginmatcher(re.compile(r""))(MyPlugin)

        assert str(cm.value) == "MyPlugin is not a Plugin"

    def test_named_duplicate(self):
        class MyPlugin(FakePlugin):
            pass

        matcher = pluginmatcher(re.compile(r"http://foo"), name="foo")

        with pytest.raises(ValueError, match=r"^A matcher named 'foo' has already been registered$"):
            matcher(matcher(MyPlugin))

    def test_no_matchers(self):
        class MyPlugin(FakePlugin):
            pass

        plugin = MyPlugin(Mock(), "http://foo")
        assert plugin.url == "http://foo"
        assert plugin.matchers == []
        assert plugin.matches == []
        assert plugin.matcher is None
        assert plugin.match is None

    def test_matchers(self):
        @pluginmatcher(re.compile(r"foo", re.VERBOSE))
        @pluginmatcher(re.compile(r"bar"), priority=HIGH_PRIORITY)
        @pluginmatcher(re.compile(r"baz"), priority=HIGH_PRIORITY, name="baz")
        class MyPlugin(FakePlugin):
            pass

        assert MyPlugin.matchers == [
            Matcher(re.compile(r"foo", re.VERBOSE), NORMAL_PRIORITY),
            Matcher(re.compile(r"bar"), HIGH_PRIORITY),
            Matcher(re.compile(r"baz"), HIGH_PRIORITY, "baz"),
        ]

    def test_matchers_inheritance(self):
        @pluginmatcher(re.compile(r"foo"))
        @pluginmatcher(re.compile(r"bar"))
        class PluginOne(FakePlugin):
            pass

        @pluginmatcher(re.compile(r"baz"))
        @pluginmatcher(re.compile(r"qux"))
        class PluginTwo(PluginOne):
            pass

        assert PluginOne.matchers is not PluginTwo.matchers
        assert PluginOne.matchers == [
            Matcher(re.compile(r"foo"), NORMAL_PRIORITY),
            Matcher(re.compile(r"bar"), NORMAL_PRIORITY),
        ]
        assert PluginTwo.matchers == [
            Matcher(re.compile(r"baz"), NORMAL_PRIORITY),
            Matcher(re.compile(r"qux"), NORMAL_PRIORITY),
            Matcher(re.compile(r"foo"), NORMAL_PRIORITY),
            Matcher(re.compile(r"bar"), NORMAL_PRIORITY),
        ]

    # noinspection PyUnusedLocal
    def test_matchers_inheritance_named_duplicate(self):
        @pluginmatcher(name="foo", pattern=re.compile(r"foo"))
        class PluginOne(FakePlugin):
            pass

        with pytest.raises(ValueError, match=r"^A matcher named 'foo' has already been registered$"):

            @pluginmatcher(name="foo", pattern=re.compile(r"foo"))
            class PluginTwo(PluginOne):
                pass

    def test_url_setter(self):
        @pluginmatcher(re.compile(r"http://(foo)"))
        @pluginmatcher(re.compile(r"http://(bar)"))
        @pluginmatcher(re.compile(r"http://(baz)"))
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
        @pluginmatcher(re.compile(r"http://foo"), name="foo")
        @pluginmatcher(re.compile(r"http://bar"), name="bar")
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

    def test_pluginargument_type_registry(self):
        assert _PLUGINARGUMENT_TYPE_REGISTRY
        assert all(callable(value) for value in _PLUGINARGUMENT_TYPE_REGISTRY.values())

    @pytest.mark.parametrize("pluginclass", [DecoratedPlugin, ClassAttrPlugin])
    def test_arguments(self, pluginclass):
        assert pluginclass.arguments is not None
        assert tuple(arg.name for arg in pluginclass.arguments) == ("foo", "bar", "baz"), "Argument name"
        assert tuple(arg.dest for arg in pluginclass.arguments) == ("_foo", "_bar", "_baz"), "Argument keyword"
        assert tuple(arg.options.get("help") for arg in pluginclass.arguments) == ("FOO", "BAR", "BAZ"), "argparse keyword"

    @pytest.mark.parametrize("pluginclass", [DecoratedPlugin, ClassAttrPlugin])
    def test_arguments_mixed(self, pluginclass):
        @pluginargument("qux")
        class MixedPlugin(pluginclass):
            pass

        assert tuple(arg.name for arg in MixedPlugin.arguments) == ("qux", "foo", "bar", "baz")

    def test_arguments_inheritance(self):
        @pluginargument("foo", help="FOO")
        @pluginargument("bar", help="BAR")
        class PluginOne(FakePlugin):
            pass

        @pluginargument("baz", help="BAZ")
        @pluginargument("qux", help="QUX")
        class PluginTwo(PluginOne):
            pass

        assert PluginOne.arguments is not PluginTwo.arguments
        assert tuple(arg.name for arg in PluginOne.arguments) == ("foo", "bar")
        assert tuple(arg.name for arg in PluginTwo.arguments) == ("baz", "qux", "foo", "bar")

    @pytest.mark.parametrize(
        ("options", "args", "expected", "raises"),
        [
            pytest.param(
                {"type": "int"},
                ["--myplugin-foo", "123"],
                123,
                nullcontext(),
                id="int",
            ),
            pytest.param(
                {"type": "float"},
                ["--myplugin-foo", "123.456"],
                123.456,
                nullcontext(),
                id="float",
            ),
            pytest.param(
                {"type": "bool"},
                ["--myplugin-foo", "yes"],
                True,
                nullcontext(),
                id="bool",
            ),
            pytest.param(
                {"type": "keyvalue"},
                ["--myplugin-foo", "key=value"],
                ("key", "value"),
                nullcontext(),
                id="keyvalue",
            ),
            pytest.param(
                {"type": "comma_list_filter", "type_args": (["one", "two", "four"],)},
                ["--myplugin-foo", "one,two,three,four"],
                ["one", "two", "four"],
                nullcontext(),
                id="comma_list_filter - args",
            ),
            pytest.param(
                {"type": "comma_list_filter", "type_kwargs": {"acceptable": ["one", "two", "four"]}},
                ["--myplugin-foo", "one,two,three,four"],
                ["one", "two", "four"],
                nullcontext(),
                id="comma_list_filter - kwargs",
            ),
            pytest.param(
                {"type": "hours_minutes_seconds"},
                ["--myplugin-foo", "1h2m3s"],
                3723,
                nullcontext(),
                id="hours_minutes_seconds",
            ),
            pytest.param(
                {"type": "UNKNOWN"},
                None,
                None,
                pytest.raises(TypeError),
                id="UNKNOWN",
            ),
        ],
    )
    def test_type_argument_map(self, options: dict, args: list, expected: Any, raises: nullcontext):
        class MyPlugin(FakePlugin):
            pass

        with raises:
            pluginargument("foo", **options)(MyPlugin)
            assert MyPlugin.arguments is not None
            pluginarg = MyPlugin.arguments.get("foo")
            assert pluginarg

            parser = argparse.ArgumentParser()
            parser.add_argument(pluginarg.argument_name("myplugin"), **pluginarg.options)
            namespace = parser.parse_args(args)
            assert namespace.myplugin_foo == expected

    def test_decorator_typeerror(self):
        with patch("builtins.repr", Mock(side_effect=lambda obj: obj.__name__)):
            with pytest.raises(TypeError) as cm:
                # noinspection PyUnusedLocal
                @pluginargument("foo")
                class Foo:
                    pass

        assert str(cm.value) == "Foo is not a Plugin"

    def test_empty(self):
        assert FakePlugin.arguments is not None
        assert tuple(iter(FakePlugin.arguments)) == ()


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
    def logger(self, pluginclass: type[Plugin]):
        with patch("streamlink.plugin.plugin.logging") as mock_logging:
            yield mock_logging.getLogger(pluginclass.__module__)

    @pytest.fixture()
    def plugin(self, pluginclass: type[Plugin], session: Streamlink, plugincache: Mock, logger: Mock):
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
        [
            {
                "__cookie:test-name1:test.se:80:/": _create_cookie_dict("test-name1", "test-value1"),
                "__cookie:test-name2:test.se:80:/": _create_cookie_dict("test-name2", "test-value2"),
                "unrelated": "data",
            },
        ],
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
        assert plugincache.set.call_args_list == [
            call(
                "__cookie:test-name1:test.se:80:/",
                self.create_cookie_dict("test-name1", "test-value1", None),
                3600,
            ),
        ]
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
        assert plugincache.set.call_args_list == [
            call(
                "__cookie:test-name:test.se:80:/",
                self.create_cookie_dict("test-name", "test-value", 3600),
                3600,
            ),
        ]

    @pytest.mark.parametrize(
        "plugincache",
        [
            {
                "__cookie:test-name1:test.se:80:/": _create_cookie_dict("test-name1", "test-value1", None),
                "__cookie:test-name2:test.se:80:/": _create_cookie_dict("test-name2", "test-value2", None),
                "unrelated": "data",
            },
        ],
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
        [
            {
                "__cookie:test-name1:test.se:80:/": _create_cookie_dict("test-name1", "test-value1", None),
                "__cookie:test-name2:test.se:80:/": _create_cookie_dict("test-name2", "test-value2", None),
                "unrelated": "data",
            },
        ],
        indirect=True,
    )
    def test_clear_filter(self, session: Streamlink, plugin: Plugin, plugincache: Mock):
        assert tuple(session.http.cookies.keys()) == ("test-name1", "test-name2")

        plugin.clear_cookies(lambda cookie: cookie.name == "test-name2")
        assert call("__cookie:test-name1:test.se:80:/", None, 0) not in plugincache.set.call_args_list
        assert call("__cookie:test-name2:test.se:80:/", None, 0) in plugincache.set.call_args_list
        assert tuple(session.http.cookies.keys()) == ("test-name1",)


@pytest.mark.parametrize(
    ("params", "expected"),
    [
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
    ],
)
def test_parse_params(params, expected):
    assert parse_params(params) == expected


@pytest.mark.parametrize(
    ("weight", "expected"),
    [
        ("720p", (720, "pixels")),
        ("720p+", (721, "pixels")),
        ("720p60", (780, "pixels")),
    ],
)
def test_stream_weight_value(weight, expected):
    assert stream_weight(weight) == expected


@pytest.mark.parametrize(
    ("weight_a", "operator", "weight_b"),
    [
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
    ],
)
def test_stream_weight(weight_a, weight_b, operator):
    assert operator(stream_weight(weight_a), stream_weight(weight_b))
