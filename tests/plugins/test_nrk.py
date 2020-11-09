import unittest

from streamlink.plugins.nrk import NRK


class TestPluginNRK(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://tv.nrk.no/direkte/nrk1',
            'https://tv.nrk.no/direkte/nrk2',
            'https://tv.nrk.no/direkte/nrk3',
            'https://tv.nrk.no/direkte/nrksuper',

            'https://tv.nrk.no/serie/nytt-paa-nytt/2020/MUHH43003020',
            'https://tv.nrk.no/serie/kongelige-fotografer/sesong/1/episode/2/avspiller',

            'https://tv.nrk.no/program/NNFA51102617',

            'https://radio.nrk.no/direkte/p1',
            'https://radio.nrk.no/direkte/p2',

            'https://radio.nrk.no/podkast/oppdatert/l_5005d62a-7f4f-4581-85d6-2a7f4f2581f2',
        ]
        for url in should_match:
            self.assertTrue(NRK.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://tv.nrk.no/',
            'https://radio.nrk.no/',
            'https://nrk.no/',
        ]
        for url in should_not_match:
            self.assertFalse(NRK.can_handle_url(url))
