import os.path
import re
import sys

from streamlink import Streamlink

if sys.version_info[0:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest


class TestPluginMatrix(unittest.TestCase):
    """
    Test that each plugin has an entry in the plugin matrix
    """
    longMessage = False
    built_in_plugins = ['akamaihd', 'http', 'hds', 'rtmp', 'hls', 'dash']

    title_re = re.compile("\n[= ]+\n")
    plugin_re = re.compile("^([\w_]+)\s", re.MULTILINE)

    def setUp(self):
        self.session = Streamlink()
        docs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../docs"))

        with open(os.path.join(docs_dir, "plugin_matrix.rst")) as plfh:
            parts = self.title_re.split(plfh.read())
            self.plugins_in_docs = list(self.plugin_re.findall(parts[3]))

    def test_plugin_has_docs_matrix(self):
        for pname in self.session.plugins.keys():
            if pname not in self.built_in_plugins:
                self.assertIn(pname, self.plugins_in_docs, "{0} is not in plugin matrix".format(pname))


    def test_docs_matrix_has_plugin(self):
        for pname in self.plugins_in_docs:
            self.assertIn(pname, self.session.plugins, "{0} plugin does not exist".format(pname))

