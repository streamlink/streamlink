import unittest

from streamlink.plugins.metube import MeTube


class TestPluginMeTube(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            'https://www.metube.id/live/METROTV',
            'https://www.metube.id/live/GTV',
            'https://www.metube.id/videos/16881738/yudi_28_bogor_-amazingakak',
            'https://www.metube.id/videos/16873428/liverpool-vs-psg-3-2-goals-and-highlights-2018',
        ]
        for url in should_match:
            self.assertTrue(MeTube.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            'https://www.metube.id/me/IMAA2018',
            'https://www.metube.id/auditions',
            'https://www.twitch.tv/twitch'
        ]
        for url in should_not_match:
            self.assertFalse(MeTube.can_handle_url(url))
