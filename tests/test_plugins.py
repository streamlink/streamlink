import os.path
import pkgutil
import unittest

import streamlink.plugins
from streamlink.plugin.plugin import Matcher, Plugin
from streamlink.utils.module import load_module


class PluginTestMeta(type):
    def __new__(mcs, name, bases, dict):
        plugin_path = os.path.dirname(streamlink.plugins.__file__)

        def gentest(plugin):
            def load_plugin_test(self):
                assert hasattr(plugin, "__plugin__"), "It exports __plugin__"

                pluginclass = plugin.__plugin__
                assert issubclass(plugin.__plugin__, Plugin), "__plugin__ is an instance of the Plugin class"

                classname = pluginclass.__name__
                assert classname == classname[0].upper() + classname[1:], "__plugin__ class name starts with uppercase letter"
                assert "_" not in classname, "__plugin__ class name does not contain underscores"

                assert isinstance(pluginclass.matchers, list) and len(pluginclass.matchers) > 0, "Has at least one matcher"
                assert all(isinstance(matcher, Matcher) for matcher in pluginclass.matchers), "Only has valid matchers"

                assert not hasattr(pluginclass, "can_handle_url"), "Does not implement deprecated can_handle_url(url)"
                assert not hasattr(pluginclass, "priority"), "Does not implement deprecated priority(url)"
                assert callable(pluginclass._get_streams), "Implements _get_streams()"

            return load_plugin_test

        pname: str
        for finder, pname, ispkg in pkgutil.iter_modules([plugin_path]):
            if pname.startswith("common_"):
                continue
            plugin_module = load_module(f"streamlink.plugins.{pname}", plugin_path)
            dict[f"test_{pname}_load"] = gentest(plugin_module)

        return type.__new__(mcs, name, bases, dict)


class TestPlugins(unittest.TestCase, metaclass=PluginTestMeta):
    """
    Test that each plugin can be loaded and does not fail when calling can_handle_url.
    """
