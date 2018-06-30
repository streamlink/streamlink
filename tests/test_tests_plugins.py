import os.path
import re
import unittest

from glob import glob
from streamlink import Streamlink


class TestPluginTests(unittest.TestCase):
    '''
    Test that each plugin has a test file
    '''
    longMessage = False
    ignore_plugins = [
        'akamaihd', 'http', 'hds', 'rtmp', 'hls', 'dash', 'stream',
    ]

    def setUp(self):
        self.session = Streamlink()

        tests_plugins_dir = os.path.abspath(os.path.join(
            os.path.dirname(__file__), 'plugins'))
        tests_plugin_files = glob(os.path.join(tests_plugins_dir, 'test_*.py'))

        self.plugins_with_tests = [
            re.sub(r'^test_([^\.]+)\.py$', r'\1',
                   os.path.split(p)[1]) for p in tests_plugin_files
        ]

    def test_plugin_has_tests(self):
        for pname in self.session.plugins.keys():
            if pname not in self.ignore_plugins:
                self.assertIn(pname, self.plugins_with_tests,
                              '{0} has no tests'.format(pname))

    def test_unknown_plugin_has_tests(self):
        for pname in self.plugins_with_tests:
            if pname not in self.ignore_plugins:
                self.assertIn(pname, self.session.plugins.keys(),
                              '{0} is not a plugin but has tests'.format(pname))
