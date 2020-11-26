import inspect
import os.path
import pkgutil
import unittest

import streamlink.plugins
from streamlink.plugins import Plugin
from streamlink.utils import load_module


class PluginTestMeta(type):
    def __new__(mcs, name, bases, dict):
        plugin_path = os.path.dirname(streamlink.plugins.__file__)
        plugins = []
        for loader, pname, ispkg in pkgutil.iter_modules([plugin_path]):
            module = load_module(f"streamlink.plugins.{pname}", plugin_path)
            if hasattr(module, "__plugin__"):
                plugins.append((loader, pname))

        def gentest(loader, pname):
            def load_plugin_test(self):
                plugin = loader.find_module(pname).load_module(pname)
                assert hasattr(plugin, "__plugin__"), "It exports __plugin__"
                assert issubclass(plugin.__plugin__, Plugin), "__plugin__ is an instance of the Plugin class"

                assert callable(plugin.__plugin__._get_streams), "The plugin implements _get_streams"
                assert callable(plugin.__plugin__.can_handle_url), "The plugin implements can_handle_url"
                sig = inspect.signature(plugin.__plugin__.can_handle_url)
                assert str(sig) == "(url)", "can_handle_url only accepts the url arg"

            return load_plugin_test

        for loader, pname in plugins:
            dict[f"test_{pname}_load"] = gentest(loader, pname)

        return type.__new__(mcs, name, bases, dict)


class TestPlugins(unittest.TestCase, metaclass=PluginTestMeta):
    """
    Test that each plugin can be loaded and does not fail when calling can_handle_url.
    """
