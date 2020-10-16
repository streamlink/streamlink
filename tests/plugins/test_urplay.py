import unittest

from streamlink.plugins.urplay import URPlay


class TestPluginURPlay(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://urplay.se/program/217458-lex-lapidus-rattssystemet-i-usa',
            'https://urplay.se/program/178137-livet-i-bokstavslandet-alfabetet',
            'https://urplay.se/program/212550-15-grader-ostlig-langd-djurliv-och-vacker-natur',
            'https://urplay.se/program/217715-ajankohtaista-suomeksi-2020-10-03',
        ]
        for url in should_match:
            self.assertTrue(URPlay.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://www.ur.se/aktuellt#clara-henry-johanna-franden-och-nadim-ghazale-utmanar-alla-sjundeklassare',
            'https://example.com/index.html',
        ]
        for url in should_not_match:
            self.assertFalse(URPlay.can_handle_url(url))
