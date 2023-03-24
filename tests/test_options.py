import argparse
import unittest
from unittest.mock import Mock, patch

import pytest

from streamlink.exceptions import StreamlinkDeprecationWarning
from streamlink.options import Argument, Arguments, Options
from streamlink.plugin import Plugin, pluginargument
from streamlink_cli.argparser import ArgumentParser
from streamlink_cli.main import setup_plugin_args, setup_plugin_options


class TestOptions(unittest.TestCase):
    def setUp(self):
        self.options = Options({
            "a_default": "default",
            "another-default": "default2",
        })

    def test_options(self):
        assert self.options.get("a_default") == "default"
        assert self.options.get("non_existing") is None

        self.options.set("a_option", "option")
        assert self.options.get("a_option") == "option"

    def test_options_update(self):
        assert self.options.get("a_default") == "default"
        assert self.options.get("non_existing") is None

        self.options.update({"a_option": "option"})
        assert self.options.get("a_option") == "option"

    def test_options_name_normalised(self):
        assert self.options.get("a_default") == "default"
        assert self.options.get("a-default") == "default"
        assert self.options.get("another-default") == "default2"
        assert self.options.get("another_default") == "default2"


class TestMappedOptions:
    class MappedOptions(Options):
        def _get_uppercase(self, key):
            return self.get_explicit(key.upper())

        def _get_add(self, key):
            return int(self.get_explicit(key)) + 1

        def _set_uppercase(self, key, value):
            self.set_explicit(key.upper(), value)

        def _set_add(self, key, value):
            self.set_explicit(key, int(value) + 1)

        _MAP_GETTERS = {
            "foo-bar": _get_uppercase,
            "baz": _get_add,
        }

        _MAP_SETTERS = {
            "foo-bar": _set_uppercase,
            "baz": _set_add,
        }

    @pytest.fixture()
    def options(self):
        return self.MappedOptions({"foo-bar": 123, "baz": 100})

    def test_mapped_key(self, options: MappedOptions):
        assert options.get("foo-bar") is None
        assert options.get("foo_bar") is None
        assert options.get_explicit("foo-bar") == 123
        assert options.get_explicit("foo_bar") == 123
        assert options.get_explicit("FOO-BAR") is None
        assert options.get_explicit("FOO_BAR") is None

        options.set("foo-bar", 321)
        assert options.get("foo-bar") == 321
        assert options.get("foo_bar") == 321
        assert options.get_explicit("foo-bar") == 123
        assert options.get_explicit("foo_bar") == 123
        assert options.get_explicit("FOO-BAR") == 321
        assert options.get_explicit("FOO_BAR") == 321

    def test_mapped_value(self, options: MappedOptions):
        assert options.get("baz") == 101
        assert options.get_explicit("baz") == 100

        options.set("baz", 0)
        assert options.get("baz") == 2
        assert options.get_explicit("baz") == 1

    def test_mutablemapping_methods(self, options: MappedOptions):
        options["key"] = "value"
        assert options["key"] == "value"

        assert options["foo-bar"] is None

        options["baz"] = 0
        assert options["baz"] == 2

        assert "foo-bar" in options
        assert "qux" not in options

        assert len(options) == 3

        assert list(iter(options)) == ["foo-bar", "baz", "key"]
        assert list(options.keys()) == ["foo-bar", "baz", "key"]
        assert list(options.values()) == [123, 1, "value"]
        assert list(options.items()) == [("foo-bar", 123), ("baz", 1), ("key", "value")]


class TestArgument(unittest.TestCase):
    def test_name(self):
        assert Argument("test-arg").argument_name("plugin") == "--plugin-test-arg"
        assert Argument("test-arg").namespace_dest("plugin") == "plugin_test_arg"
        assert Argument("test-arg").dest == "test_arg"

    def test_name_plugin(self):
        assert Argument("test-arg").argument_name("test_plugin") == "--test-plugin-test-arg"
        assert Argument("test-arg").namespace_dest("test_plugin") == "test_plugin_test_arg"
        assert Argument("test-arg").dest == "test_arg"

    def test_name_override(self):
        assert Argument("test", argument_name="override-name").argument_name("plugin") == "--override-name"
        assert Argument("test", argument_name="override-name").namespace_dest("plugin") == "override_name"
        assert Argument("test", argument_name="override-name").dest == "test"


class TestArguments(unittest.TestCase):
    def test_getter(self):
        test1 = Argument("test1")
        test2 = Argument("test2")
        args = Arguments(test1, test2)

        assert args.get("test1") == test1
        assert args.get("test2") == test2
        assert args.get("test3") is None

    def test_iter(self):
        test1 = Argument("test1")
        test2 = Argument("test2")
        args = Arguments(test1, test2)

        i_args = iter(args)

        assert next(i_args) == test1
        assert next(i_args) == test2

    def test_requires(self):
        test1 = Argument("test1", requires="test2")
        test2 = Argument("test2", requires="test3")
        test3 = Argument("test3")

        args = Arguments(test1, test2, test3)

        assert list(args.requires("test1")) == [test2, test3]

    def test_requires_invalid(self):
        test1 = Argument("test1", requires="test2")

        args = Arguments(test1)

        with pytest.raises(KeyError):
            list(args.requires("test1"))

    def test_requires_cycle(self):
        test1 = Argument("test1", requires="test2")
        test2 = Argument("test2", requires="test1")

        args = Arguments(test1, test2)

        with pytest.raises(RuntimeError):
            list(args.requires("test1"))

    def test_requires_cycle_deep(self):
        test1 = Argument("test1", requires="test-2")
        test2 = Argument("test-2", requires="test3")
        test3 = Argument("test3", requires="test1")

        args = Arguments(test1, test2, test3)

        with pytest.raises(RuntimeError):
            list(args.requires("test1"))

    def test_requires_cycle_self(self):
        test1 = Argument("test1", requires="test1")

        args = Arguments(test1)

        with pytest.raises(RuntimeError):
            list(args.requires("test1"))


class TestSetupOptions:
    def test_setup_plugin_args(self, recwarn: pytest.WarningsRecorder):
        session = Mock()
        plugin = Mock()
        parser = ArgumentParser(add_help=False)
        parser.add_argument("--global-arg1", default=123)
        parser.add_argument("--global-arg2", default=456)

        session.plugins = {"mock": plugin}
        plugin.arguments = Arguments(
            Argument("global-arg1", is_global=True),
            Argument("test1", default="default1"),
            Argument("test2", default="default2"),
            Argument("test3"),
        )

        assert [(record.category, str(record.message)) for record in recwarn.list] == [
            (StreamlinkDeprecationWarning, "Defining global plugin arguments is deprecated. Use the session options instead."),
        ]

        setup_plugin_args(session, parser)

        group_plugins = next((grp for grp in parser._action_groups if grp.title == "Plugin options"), None)  # pragma: no branch
        assert group_plugins is not None, "Adds the 'Plugin options' arguments group"
        assert group_plugins in parser.NESTED_ARGUMENT_GROUPS[None], "Adds the 'Plugin options' arguments group"
        group_plugin = next((grp for grp in parser._action_groups if grp.title == "Mock"), None)  # pragma: no branch
        assert group_plugin is not None, "Adds the 'Mock' arguments group"
        assert group_plugin in parser.NESTED_ARGUMENT_GROUPS[group_plugins], "Adds the 'Mock' arguments group"
        assert [item for action in group_plugin._group_actions for item in action.option_strings] \
            == ["--mock-test1", "--mock-test2", "--mock-test3"], \
            "Only adds plugin arguments and ignores global argument references"
        assert [item for action in parser._actions for item in action.option_strings] \
            == ["--global-arg1", "--global-arg2", "--mock-test1", "--mock-test2", "--mock-test3"], \
            "Parser has all arguments registered"

        assert plugin.options.get("global-arg1") == 123
        assert plugin.options.get("global-arg2") is None
        assert plugin.options.get("test1") == "default1"
        assert plugin.options.get("test2") == "default2"
        assert plugin.options.get("test3") is None

    def test_setup_plugin_options(self, recwarn: pytest.WarningsRecorder):
        @pluginargument("foo-foo", is_global=True)
        @pluginargument("bar-bar", default=456)
        @pluginargument("baz-baz", default=789, help=argparse.SUPPRESS)
        class FakePlugin(Plugin):
            def _get_streams(self):  # pragma: no cover
                pass

        assert [(record.category, str(record.message), record.filename) for record in recwarn.list] == [
            (
                StreamlinkDeprecationWarning,
                "Defining global plugin arguments is deprecated. Use the session options instead.",
                __file__,
            ),
        ]

        session = Mock()
        parser = ArgumentParser()
        parser.add_argument("--foo-foo", default=123)

        session.plugins = {"plugin": FakePlugin}
        session.set_plugin_option = lambda name, key, value: session.plugins[name].options.update({key: value})

        with patch("streamlink_cli.main.args") as args:
            args.foo_foo = 321
            args.plugin_bar_bar = 654
            args.plugin_baz_baz = 987  # this wouldn't be set by the parser if the argument is suppressed

            setup_plugin_args(session, parser)
            assert FakePlugin.options.get("foo_foo") == 123, "Sets the global-argument's default value"
            assert FakePlugin.options.get("bar_bar") == 456, "Sets the plugin-argument's default value"
            assert FakePlugin.options.get("baz_baz") == 789, "Sets the suppressed plugin-argument's default value"

            setup_plugin_options(session, "plugin", FakePlugin)
            assert FakePlugin.options.get("foo_foo") == 321, "Sets the provided global-argument value"
            assert FakePlugin.options.get("bar_bar") == 654, "Sets the provided plugin-argument value"
            assert FakePlugin.options.get("baz_baz") == 789, "Doesn't set values of suppressed plugin-arguments"
