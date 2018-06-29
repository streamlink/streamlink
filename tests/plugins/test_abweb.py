import unittest

from streamlink.plugins.abweb import ABweb


class TestPluginABweb(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'http://www.abweb.com/bis-tv-online/bistvo-tele-universal.aspx?chn=ab1',
            'http://www.abweb.com/BIS-TV-Online/bistvo-tele-universal.aspx?chn=ab1',
            'http://www.abweb.com/BIS-TV-Online/bistvo-tele-universal.aspx?chn=luckyjack',
        ]
        for url in should_match:
            self.assertTrue(ABweb.can_handle_url(url))

        should_not_match = [
            'http://www.abweb.com',
        ]
        for url in should_not_match:
            self.assertFalse(ABweb.can_handle_url(url))
