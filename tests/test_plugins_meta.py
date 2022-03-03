import os.path
import re
import unittest

from streamlink import Streamlink


class TestPluginMeta(unittest.TestCase):
    """
    Test that each plugin has an entry in the plugin matrix and a test file
    """
    longMessage = False

    protocol_tests = ["http", "hls", "dash", "stream", "rtmp"]

    @classmethod
    def setUpClass(cls):
        cls.session = Streamlink()
        docs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../docs"))

        with open(os.path.join(docs_dir, "plugin_matrix.rst")) as plfh:
            parts = re.split(r"\n[= ]+\n", plfh.read())
            cls.plugins_in_docs = list(re.findall(r"^([\w_]+)\s", parts[3], re.MULTILINE))

        cls.plugins = cls.session.plugins.keys()
        cls.plugins_no_protocols = [pname for pname in cls.plugins if pname not in cls.protocol_tests]

    def test_plugin_has_docs_matrix(self):
        for pname in self.plugins_no_protocols:
            self.assertIn(pname, self.plugins_in_docs, "{0} is not in plugin matrix".format(pname))

    def test_docs_matrix_has_plugin(self):
        for pname in self.plugins_in_docs:
            self.assertIn(pname, self.plugins_no_protocols, "{0} plugin does not exist".format(pname))
