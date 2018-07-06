import os.path
import re
import unittest

from glob import glob
from streamlink import Streamlink


class TestPluginMeta(unittest.TestCase):
    """
    Test that each plugin has an entry in the plugin matrix and a test file
    """
    longMessage = False
    built_in_plugins = [
        "akamaihd", "http", "hds", "rtmp", "hls", "dash", "stream"
    ]

    title_re = re.compile(r"\n[= ]+\n")
    plugin_re = re.compile(r"^([\w_]+)\s", re.MULTILINE)

    def setUp(self):
        self.session = Streamlink()
        docs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                "../docs"))

        with open(os.path.join(docs_dir, "plugin_matrix.rst")) as plfh:
            parts = self.title_re.split(plfh.read())
            self.plugins_in_docs = list(self.plugin_re.findall(parts[3]))

        tests_plugins_dir = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "plugins"))
        tests_plugin_files = glob(os.path.join(tests_plugins_dir, "test_*.py"))

        self.plugins_with_tests = [
            re.sub(r"^test_([^\.]+)\.py$", r"\1",
                   os.path.split(p)[1]) for p in tests_plugin_files
        ]

    def test_plugin_has_docs_matrix(self):
        for pname in self.session.plugins.keys():
            if pname not in self.built_in_plugins:
                self.assertIn(pname, self.plugins_in_docs,
                              "{0} is not in plugin matrix".format(pname))

    def test_docs_matrix_has_plugin(self):
        for pname in self.plugins_in_docs:
            self.assertIn(pname, self.session.plugins,
                          "{0} plugin does not exist".format(pname))

    def test_plugin_has_tests(self):
        for pname in self.session.plugins.keys():
            if pname not in self.built_in_plugins:
                self.assertIn(pname, self.plugins_with_tests,
                              "{0} has no tests".format(pname))

    def test_unknown_plugin_has_tests(self):
        for pname in self.plugins_with_tests:
            if pname not in self.built_in_plugins:
                self.assertIn(pname, self.session.plugins.keys(),
                              "{0} is not a plugin but has tests".format(pname))
