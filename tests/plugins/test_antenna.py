import unittest

from streamlink.plugins.antenna import Antenna


class TestPluginAntenna(unittest.TestCase):

    ''' Plugin Broken '''
    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(Antenna.can_handle_url(url))
