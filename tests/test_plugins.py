import pkgutil

import pytest

import streamlink.plugins
# from streamlink.plugins import Plugin
from streamlink.plugin.plugin import Matcher, Plugin
from streamlink.utils.module import load_module


plugins_path = streamlink.plugins.__path__[0]
plugins = [
    pname
    for finder, pname, ispkg in pkgutil.iter_modules([plugins_path])
    if not pname.startswith("common_")
]


class TestPlugins:
    @pytest.fixture(scope="class", params=plugins)
    def plugin(self, request):
        return load_module(request.param, plugins_path)

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
