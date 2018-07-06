import unittest

from streamlink.plugins.nrk import NRK


class TestPluginNRK(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://tv.nrk.no/direkte/nrk1',
            'https://tv.nrk.no/direkte/nrk2',
            'https://tv.nrk.no/direkte/nrk3',
            'https://tv.nrk.no/direkte/nrksuper',
            'https://radio.nrk.no/direkte/p1',
            'https://radio.nrk.no/direkte/p2',
        ]
        for url in should_match:
            self.assertTrue(NRK.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://nrk.no/',
        ]
        for url in should_not_match:
            self.assertFalse(NRK.can_handle_url(url))
