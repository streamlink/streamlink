import os.path
import re
import unittest
from glob import glob

from streamlink import Streamlink, plugins as streamlinkplugins
from streamlink_cli.argparser import build_parser


class TestPluginMeta(unittest.TestCase):
    """
    Test that each plugin has an entry in the plugin matrix and a test file
    """
    longMessage = False

    protocol_tests = ["http", "hls", "dash", "stream"]

    @classmethod
    def setUpClass(cls):
        cls.session = Streamlink()
        docs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../docs"))
        plugins_dir = streamlinkplugins.__path__[0]

        with open(os.path.join(docs_dir, "plugin_matrix.rst")) as plfh:
            parts = re.split(r"\n[= ]+\n", plfh.read())
            cls.plugins_in_docs = list(re.findall(r"^([\w_]+)\s", parts[3], re.MULTILINE))

        with open(os.path.join(plugins_dir, ".removed")) as rmfh:
            cls.plugins_removed = [pname for pname in rmfh.read().split("\n") if pname and not pname.startswith("#")]

        tests_plugins_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "plugins"))
        tests_plugin_files = glob(os.path.join(tests_plugins_dir, "test_*.py"))

        cls.plugins = cls.session.plugins.keys()
        cls.plugin_tests = [re.sub(r"^test_(.+)\.py$", r"\1", os.path.basename(file)) for file in tests_plugin_files]
        cls.plugins_no_protocols = [pname for pname in cls.plugins if pname not in cls.protocol_tests]
        cls.plugin_tests_no_protocols = [pname for pname in cls.plugin_tests if pname not in cls.protocol_tests]

    def test_plugin_has_docs_matrix(self):
        for pname in self.plugins_no_protocols:
            self.assertIn(pname, self.plugins_in_docs, f"{pname} is not in plugin matrix")

    def test_docs_matrix_has_plugin(self):
        for pname in self.plugins_in_docs:
            self.assertIn(pname, self.plugins_no_protocols, f"{pname} plugin does not exist")

    def test_plugin_has_tests(self):
        for pname in self.plugins_no_protocols:
            self.assertIn(pname, self.plugin_tests, f"{pname} has no tests")

    def test_unknown_plugin_has_tests(self):
        for pname in self.plugin_tests_no_protocols:
            self.assertIn(pname, self.plugins_no_protocols, f"{pname} is not a plugin but has tests")

    def test_plugin_not_in_removed_list(self):
        for pname in self.plugins:
            self.assertNotIn(pname, self.plugins_removed, f"{pname} is in removed plugins list")

    def test_removed_list_is_sorted(self):
        plugins_removed_sorted = self.plugins_removed.copy()
        plugins_removed_sorted.sort()
        self.assertEqual(self.plugins_removed, plugins_removed_sorted, "Removed plugins list is not sorted alphabetically")

    def test_plugin_has_valid_global_args(self):
        parser = build_parser()
        global_arg_dests = [action.dest for action in parser._actions]
        for pname, plugin in self.session.plugins.items():
            for parg in plugin.arguments:
                if not parg.is_global:  # pragma: no cover
                    continue
                self.assertIn(parg.dest, global_arg_dests, f"{parg.name} from plugins.{pname} is not a valid global argument")
