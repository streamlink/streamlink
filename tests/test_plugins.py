import os.path
import pkgutil
import six
import unittest
import logging
import pytest
import streamlink.plugins
from streamlink.plugin import Plugin

log = logging.getLogger(__name__)


class PluginTestMeta(type):
    def __new__(mcs, name, bases, dict):
        plugin_path = os.path.dirname(streamlink.plugins.__file__)
        plugins = []
        for (loader, name, _) in pkgutil.iter_modules([plugin_path]):
            print(loader)
            plugins.append((loader, name))

        def gentest(loader, name):
            def load_plugin_test(self):
                plugin = loader.find_module(name).load_module(name)
                # validate that can_handle_url does not fail
                if hasattr(plugin, "__plugin__") and issubclass(plugin.__plugin__, Plugin):
                    plugin.__plugin__.can_handle_url("http://test.com")
                else:
                    pytest.skip("{0} is not a plugin module".format(name))

            return load_plugin_test

        for loader, name in plugins:
            dict['test_{0}_load'.format(name)] = gentest(loader, name)

        return type.__new__(mcs, name, bases, dict)


@six.add_metaclass(PluginTestMeta)
class TestPlugins(unittest.TestCase):
    """
    Test that each plugin can be loaded and does not fail when calling can_handle_url.
    """
