import imp
import os.path
import pkgutil
import six

import unittest

import streamlink.plugins
from streamlink import Streamlink
from streamlink.utils import load_module


class PluginTestMeta(type):
    def __new__(mcs, name, bases, dict):
        plugin_path = os.path.dirname(streamlink.plugins.__file__)
        plugins = []
        for loader, pname, ispkg in pkgutil.iter_modules([plugin_path]):
            module = load_module(pname, plugin_path)
            if hasattr(module, "__plugin__"):
                plugins.append((pname))

        session = Streamlink()

        def gentest(pname):
            def load_plugin_test(self):
                # Reset file variable to ensure it is still open when doing
                # load_plugin else python might open the plugin source .py
                # using ascii encoding instead of utf-8.
                # See also open() call here: imp._HackedGetData.get_data
                file, pathname, desc = imp.find_module(pname, [plugin_path])
                session.load_plugin(pname, file, pathname, desc)
                # validate that can_handle_url does not fail
                session.plugins[pname].can_handle_url("http://test.com")

            return load_plugin_test

        for pname in plugins:
            dict['test_{0}_load'.format(pname)] = gentest(pname)

        return type.__new__(mcs, name, bases, dict)


@six.add_metaclass(PluginTestMeta)
class TestPlugins(unittest.TestCase):
    """
    Test that each plugin can be loaded and does not fail when calling can_handle_url.
    """
