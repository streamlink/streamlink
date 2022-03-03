import os.path
import pkgutil
import re

import pytest

import streamlink.plugins
import tests.plugins
from streamlink.plugin.plugin import Matcher, Plugin
from streamlink.utils.module import load_module
from streamlink_cli.argparser import build_parser


plugins_path = streamlink.plugins.__path__[0]
plugintests_path = tests.plugins.__path__[0]

protocol_plugins = [
    "http",
    "hls",
    "dash",
    "rtmp",
]
plugintests_ignore = [
    "test_stream",
]

plugins = [
    pname
    for finder, pname, ispkg in pkgutil.iter_modules([plugins_path])
    if not pname.startswith("common_")
]
plugins_no_protocols = [pname for pname in plugins if pname not in protocol_plugins]
plugintests = [
    re.sub(r"^test_", "", tname)
    for finder, tname, ispkg in pkgutil.iter_modules([plugintests_path])
    if tname.startswith("test_") and tname not in plugintests_ignore
]


class TestPlugins:
    @pytest.fixture(scope="class", params=plugins)
    def plugin(self, request):
        return load_module(request.param, plugins_path)

    @pytest.fixture(scope="class")
    def parser(self):
        return build_parser()

    @pytest.fixture(scope="class")
    def global_arg_dests(self, parser):
        return [action.dest for action in parser._actions]

    def test_exports_plugin(self, plugin):
        assert hasattr(plugin, "__plugin__"), "Plugin module exports __plugin__"
        assert issubclass(plugin.__plugin__, Plugin), "__plugin__ is an instance of the Plugin class"

    def test_classname(self, plugin):
        classname = plugin.__plugin__.__name__
        assert classname == classname[0].upper() + classname[1:], "__plugin__ class name starts with uppercase letter"
        assert "_" not in classname, "__plugin__ class name does not contain underscores"

    def test_matchers(self, plugin):
        pluginclass = plugin.__plugin__
        assert isinstance(pluginclass.matchers, list) and len(pluginclass.matchers) > 0, "Has at least one matcher"
        assert all(isinstance(matcher, Matcher) for matcher in pluginclass.matchers), "Only has valid matchers"

    def test_plugin_api(self, plugin):
        pluginclass = plugin.__plugin__
        assert not hasattr(pluginclass, "can_handle_url"), "Does not implement deprecated can_handle_url(url)"
        assert not hasattr(pluginclass, "priority"), "Does not implement deprecated priority(url)"
        assert callable(pluginclass._get_streams), "Implements _get_streams()"

    def test_has_valid_global_args(self, global_arg_dests, plugin):
        assert all(parg.dest in global_arg_dests for parg in plugin.__plugin__.arguments if parg.is_global), \
            "All plugin arguments with is_global=True are valid global arguments"


class TestPluginTests:
    @pytest.mark.parametrize("plugin", plugins_no_protocols)
    def test_plugin_has_tests(self, plugin):
        assert plugin in plugintests, "Test module exists for plugin"

    @pytest.mark.parametrize("plugintest", plugintests)
    def test_test_has_plugin(self, plugintest):
        assert plugintest in plugins, "Plugin exists for test module"


class TestRemovedPluginsFile:
    @pytest.fixture(scope="class")
    def removedplugins(self):
        with open(os.path.join(plugins_path, ".removed"), "r") as handle:
            return [line.strip() for line in handle.readlines() if not line.strip().startswith("#")]

    @pytest.mark.parametrize("plugin", plugins)
    def test_plugin_not_in_file(self, plugin, removedplugins):
        assert plugin not in removedplugins, "Existing plugin is not in removed plugins list"

    def test_is_sorted(self, removedplugins):
        removedplugins_sorted = removedplugins[:]
        removedplugins_sorted.sort()
        assert removedplugins_sorted == removedplugins, "Removed plugins list is sorted alphabetically"
