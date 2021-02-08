import inspect
import os.path
import pkgutil
import unittest

import six

import streamlink.plugins
from streamlink.plugins import Plugin
from streamlink.utils import load_module


class PluginTestMeta(type):
    def __new__(mcs, name, bases, dict):
        plugin_path = os.path.dirname(streamlink.plugins.__file__)
        plugins = []
        for loader, pname, ispkg in pkgutil.iter_modules([plugin_path]):
            module = load_module(pname, plugin_path)
            if hasattr(module, "__plugin__"):
                plugins.append((loader, pname))

        def gentest(loader, pname):
            def load_plugin_test(self):
                plugin = loader.find_module(pname).load_module(pname)
                assert hasattr(plugin, "__plugin__"), "It exports __plugin__"
                assert issubclass(plugin.__plugin__, Plugin), "__plugin__ is an instance of the Plugin class"

                assert callable(plugin.__plugin__._get_streams), "The plugin implements _get_streams"
                assert callable(plugin.__plugin__.can_handle_url), "The plugin implements can_handle_url"
                if hasattr(inspect, 'signature'):
                    sig = inspect.signature(plugin.__plugin__.can_handle_url)
                else:
                    argspec = inspect.getargspec(plugin.__plugin__.can_handle_url)
                    # Generate the argument list that is separated by colons.
                    args = argspec.args[:]
                    if argspec.defaults:
                        offset = len(args) - len(argspec.defaults)
                        for i, default in enumerate(argspec.defaults):
                            args[i + offset] = '{}={!r}'.format(args[i + offset], argspec.defaults[i])
                    if argspec.varargs:
                        args.append('*' + argspec.varargs)
                    if argspec.keywords:
                        args.append('**' + argspec.keywords)
                    sig = '(' + ', '.join(args[1:]) + ')'

                assert str(sig) == "(url)", "can_handle_url only accepts the url arg"

            return load_plugin_test

        for loader, pname in plugins:
            dict["test_{0}_load".format(pname)] = gentest(loader, pname)

        return type.__new__(mcs, name, bases, dict)


@six.add_metaclass(PluginTestMeta)
class TestPlugins(unittest.TestCase):
    """
    Test that each plugin can be loaded and does not fail when calling can_handle_url.
    """
