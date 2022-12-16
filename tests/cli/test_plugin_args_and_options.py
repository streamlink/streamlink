import argparse
from typing import Type
from unittest.mock import Mock, call

import pytest

from streamlink.plugin import Plugin, pluginargument
from streamlink.session import Streamlink
from streamlink_cli.argparser import ArgumentParser
from streamlink_cli.main import setup_plugin_args, setup_plugin_options


@pytest.fixture()
def parser():
    return ArgumentParser(add_help=False)


@pytest.fixture(autouse=True)
def _args(monkeypatch: pytest.MonkeyPatch):
    args = argparse.Namespace(
        mock_foo_bar=123,
        mock_baz=654,
        # mock_qux wouldn't be set by the parser if the argument is suppressed
        # its value will be ignored
        mock_qux=987,
        mock_user="username",
        mock_pass=None,
        mock_captcha=None,
    )
    monkeypatch.setattr("streamlink_cli.main.args", args)


@pytest.fixture()
def plugin():
    # simple argument which requires namespace-name normalization
    @pluginargument("foo-bar")
    # argument with default value
    @pluginargument("baz", default=456)
    # suppressed argument
    @pluginargument("qux", default=789, help=argparse.SUPPRESS)
    # required argument with dependencies
    @pluginargument("user", required=True, requires=["pass", "captcha"])
    # sensitive argument (using console.askpass if unset)
    @pluginargument("pass", sensitive=True)
    # argument with custom prompt (using console.ask if unset)
    @pluginargument("captcha", prompt="CAPTCHA code")
    class FakePlugin(Plugin):
        def _get_streams(self):  # pragma: no cover
            pass

    return FakePlugin


@pytest.fixture(autouse=True)
def session(monkeypatch: pytest.MonkeyPatch, parser: ArgumentParser, plugin: Type[Plugin]):
    monkeypatch.setattr("streamlink.session.Streamlink.load_builtin_plugins", Mock())
    session = Streamlink()
    session.plugins["mock"] = plugin

    setup_plugin_args(session, parser)

    return session


@pytest.fixture()
def console(monkeypatch: pytest.MonkeyPatch):
    console = Mock()
    monkeypatch.setattr("streamlink_cli.main.console", console)
    return console


class TestPluginArgs:
    def test_arguments(self, parser: ArgumentParser, plugin: Type[Plugin]):
        group_plugins = next((grp for grp in parser._action_groups if grp.title == "Plugin options"), None)  # pragma: no branch
        assert group_plugins is not None, "Adds the 'Plugin options' arguments group"
        assert group_plugins in parser.NESTED_ARGUMENT_GROUPS[None], "Adds the 'Plugin options' arguments group"

        group_plugin = next((grp for grp in parser._action_groups if grp.title == "Mock"), None)  # pragma: no branch
        assert group_plugin is not None, "Adds the 'Mock' arguments group"
        assert group_plugin in parser.NESTED_ARGUMENT_GROUPS[group_plugins], "Adds the 'Mock' arguments group"

        assert [
            item
            for action in parser._actions
            for item in action.option_strings
            if action.help != argparse.SUPPRESS
        ] == [
            "--mock-foo-bar",
            "--mock-baz",
            "--mock-user",
            "--mock-pass",
            "--mock-captcha",
        ], "Parser has all arguments registered"


class TestPluginOptions:
    def test_empty(self, console: Mock):
        options = setup_plugin_options("mock", Plugin)
        assert not options.defaults
        assert not options.options

        assert not console.ask.called
        assert not console.askpass.called

    def test_options(self, plugin: Type[Plugin], console: Mock):
        options = setup_plugin_options("mock", plugin)

        assert console.ask.call_args_list == [call("CAPTCHA code: ")]
        assert console.askpass.call_args_list == [call("Enter mock pass: ")]

        assert plugin.arguments
        arg_foo = plugin.arguments.get("foo-bar")
        arg_baz = plugin.arguments.get("baz")
        arg_qux = plugin.arguments.get("qux")
        assert arg_foo
        assert arg_baz
        assert arg_qux
        assert arg_foo.default is None
        assert arg_baz.default == 456
        assert arg_qux.default == 789

        assert options.get("foo-bar") == 123, "Overrides the default plugin-argument value"
        assert options.get("baz") == 654, "Uses the plugin-argument default value"
        assert options.get("qux") == 789, "Ignores values of suppressed plugin-arguments"

        options.clear()
        assert options.get("foo-bar") == arg_foo.default
        assert options.get("baz") == arg_baz.default
        assert options.get("qux") == arg_qux.default
