import argparse
import unittest
from unittest.mock import Mock, patch

from streamlink.options import Argument, Arguments, Options
from streamlink_cli.main import setup_plugin_args, setup_plugin_options


class TestOptions(unittest.TestCase):
    def setUp(self):
        self.options = Options({
            "a_default": "default",
            "another-default": "default2"
        })

    def test_options(self):
        self.assertEqual(self.options.get("a_default"), "default")
        self.assertEqual(self.options.get("non_existing"), None)

        self.options.set("a_option", "option")
        self.assertEqual(self.options.get("a_option"), "option")

    def test_options_update(self):
        self.assertEqual(self.options.get("a_default"), "default")
        self.assertEqual(self.options.get("non_existing"), None)

        self.options.update({"a_option": "option"})
        self.assertEqual(self.options.get("a_option"), "option")

    def test_options_name_normalised(self):
        self.assertEqual(self.options.get("a_default"), "default")
        self.assertEqual(self.options.get("a-default"), "default")
        self.assertEqual(self.options.get("another-default"), "default2")
        self.assertEqual(self.options.get("another_default"), "default2")


class TestArgument(unittest.TestCase):
    def test_name(self):
        self.assertEqual(Argument("test-arg").argument_name("plugin"), "--plugin-test-arg")
        self.assertEqual(Argument("test-arg").namespace_dest("plugin"), "plugin_test_arg")
        self.assertEqual(Argument("test-arg").dest, "test_arg")

    def test_name_plugin(self):
        self.assertEqual(Argument("test-arg").argument_name("test_plugin"), "--test-plugin-test-arg")
        self.assertEqual(Argument("test-arg").namespace_dest("test_plugin"), "test_plugin_test_arg")
        self.assertEqual(Argument("test-arg").dest, "test_arg")

    def test_name_override(self):
        self.assertEqual(Argument("test", argument_name="override-name").argument_name("plugin"), "--override-name")
        self.assertEqual(Argument("test", argument_name="override-name").namespace_dest("plugin"), "override_name")
        self.assertEqual(Argument("test", argument_name="override-name").dest, "test")


class TestArguments(unittest.TestCase):
    def test_getter(self):
        test1 = Argument("test1")
        test2 = Argument("test2")
        args = Arguments(test1, test2)

        self.assertEqual(args.get("test1"), test1)
        self.assertEqual(args.get("test2"), test2)
        self.assertEqual(args.get("test3"), None)

    def test_iter(self):
        test1 = Argument("test1")
        test2 = Argument("test2")
        args = Arguments(test1, test2)

        i_args = iter(args)

        self.assertEqual(next(i_args), test1)
        self.assertEqual(next(i_args), test2)

    def test_requires(self):
        test1 = Argument("test1", requires="test2")
        test2 = Argument("test2", requires="test3")
        test3 = Argument("test3")

        args = Arguments(test1, test2, test3)

        self.assertEqual(list(args.requires("test1")), [test2, test3])

    def test_requires_invalid(self):
        test1 = Argument("test1", requires="test2")

        args = Arguments(test1)

        self.assertRaises(KeyError, lambda: list(args.requires("test1")))

    def test_requires_cycle(self):
        test1 = Argument("test1", requires="test2")
        test2 = Argument("test2", requires="test1")

        args = Arguments(test1, test2)

        self.assertRaises(RuntimeError, lambda: list(args.requires("test1")))

    def test_requires_cycle_deep(self):
        test1 = Argument("test1", requires="test-2")
        test2 = Argument("test-2", requires="test3")
        test3 = Argument("test3", requires="test1")

        args = Arguments(test1, test2, test3)

        self.assertRaises(RuntimeError, lambda: list(args.requires("test1")))

    def test_requires_cycle_self(self):
        test1 = Argument("test1", requires="test1")

        args = Arguments(test1)

        self.assertRaises(RuntimeError, lambda: list(args.requires("test1")))


class TestSetupOptions(unittest.TestCase):
    def test_setup_plugin_args(self):
        session = Mock()
        plugin = Mock()
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument("--global-arg1", default=123)
        parser.add_argument("--global-arg2", default=456)

        session.plugins = {"mock": plugin}
        plugin.arguments = Arguments(
            Argument("global-arg1", is_global=True),
            Argument("test1", default="default1"),
            Argument("test2", default="default2"),
            Argument("test3")
        )

        setup_plugin_args(session, parser)

        group_plugins = next((grp for grp in parser._action_groups if grp.title == "Plugin options"), None)  # pragma: no branch
        self.assertIsNotNone(group_plugins, "Adds the 'Plugin options' arguments group")
        group_plugin = next((grp for grp in group_plugins._action_groups if grp.title == "Mock"), None)  # pragma: no branch
        self.assertIsNotNone(group_plugin, "Adds the 'Mock' arguments group to the 'Plugin options' group")
        self.assertEqual(
            [item for action in group_plugin._group_actions for item in action.option_strings],
            ["--mock-test1", "--mock-test2", "--mock-test3"],
            "Only adds plugin arguments and ignores global argument references"
        )
        self.assertEqual(
            [item for action in parser._actions for item in action.option_strings],
            ["--global-arg1", "--global-arg2", "--mock-test1", "--mock-test2", "--mock-test3"],
            "Parser has all arguments registered"
        )

        self.assertEqual(plugin.options.get("global-arg1"), 123)
        self.assertEqual(plugin.options.get("global-arg2"), None)
        self.assertEqual(plugin.options.get("test1"), "default1")
        self.assertEqual(plugin.options.get("test2"), "default2")
        self.assertEqual(plugin.options.get("test3"), None)

    def test_setup_plugin_options(self):
        session = Mock()
        plugin = Mock(module="plugin")
        parser = argparse.ArgumentParser()
        parser.add_argument("--foo-foo", default=123)

        session.plugins = {"plugin": plugin}
        session.set_plugin_option = lambda name, key, value: session.plugins[name].options.update({key: value})
        plugin.arguments = Arguments(
            Argument("foo-foo", is_global=True),
            Argument("bar-bar", default=456),
            Argument("baz-baz", default=789, help=argparse.SUPPRESS)
        )

        with patch("streamlink_cli.main.args") as args:
            args.foo_foo = 321
            args.plugin_bar_bar = 654
            args.plugin_baz_baz = 987  # this wouldn't be set by the parser if the argument is suppressed

            setup_plugin_args(session, parser)
            self.assertEqual(plugin.options.get("foo_foo"), 123, "Sets the global-argument's default value")
            self.assertEqual(plugin.options.get("bar_bar"), 456, "Sets the plugin-argument's default value")
            self.assertEqual(plugin.options.get("baz_baz"), 789, "Sets the suppressed plugin-argument's default value")

            setup_plugin_options(session, plugin)
            self.assertEqual(plugin.options.get("foo_foo"), 321, "Sets the provided global-argument value")
            self.assertEqual(plugin.options.get("bar_bar"), 654, "Sets the provided plugin-argument value")
            self.assertEqual(plugin.options.get("baz_baz"), 789, "Doesn't set values of suppressed plugin-arguments")
