import unittest

from streamlink.plugins.vgtv import VGTV


class TestPluginVGTV(unittest.TestCase):

    ''' Broken Plugin
    def test_can_handle_url(self):
        should_match = [
            'http://ap.vgtv.no/webtv/video/114339/tempo-sport-motorsykkelen-som-gjenoppstod',
            'http://ap.vgtv.no/webtv#!/video/114339/tempo-sport-motorsykkelen-som-gjenoppstod',
            'https://tv.aftonbladet.se/abtv/articles/243105',
            'https://www.vgtv.no/live/139125/sportsnyhetene-doegnet-rundt',
            'https://www.vgtv.no/video/153967/vi-fulgte-hopp-stor-bakke-menn',
        ]
        for url in should_match:
            self.assertTrue(VGTV.can_handle_url(url))
    '''

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://ap.vgtv.no',
        ]
        for url in should_not_match:
            self.assertFalse(VGTV.can_handle_url(url))
