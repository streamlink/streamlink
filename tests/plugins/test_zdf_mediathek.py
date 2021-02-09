import unittest

from streamlink.plugins.zdf_mediathek import ZDFMediathek


class TestPluginZDFMediathek(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://www.zdf.de/live-tv',
            'https://www.zdf.de/sender/zdf/zdf-live-beitrag-100.html',
            'https://www.zdf.de/sender/zdfneo/zdfneo-live-beitrag-100.html',
            'https://www.zdf.de/sender/3sat/3sat-live-beitrag-100.html',
            'https://www.zdf.de/sender/phoenix/phoenix-live-beitrag-100.html',
            'https://www.zdf.de/sender/arte/arte-livestream-100.html',
            'https://www.zdf.de/sender/kika/kika-live-beitrag-100.html',
            'https://www.zdf.de/dokumentation/zdfinfo-doku/zdfinfo-live-beitrag-100.html',
            'https://www.zdf.de/comedy/heute-show/videos/diy-hazel-habeck-100.html',
            'https://www.zdf.de/nachrichten/heute-sendungen/so-wird-das-wetter-102.html',
            'https://www.3sat.de/wissen/nano',
        ]
        for url in should_match:
            self.assertTrue(ZDFMediathek.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://www.example.com',
        ]
        for url in should_not_match:
            self.assertFalse(ZDFMediathek.can_handle_url(url))
