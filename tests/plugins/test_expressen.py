import unittest

from streamlink.plugins.expressen import Expressen


class TestPluginExpressen(unittest.TestCase):

    ''' Broken Plugin '''
    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://ap.vgtv.no',
        ]
        for url in should_not_match:
            self.assertFalse(Expressen.can_handle_url(url))
