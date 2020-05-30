import unittest

from streamlink.plugins.olympicchannel import OlympicChannel


class TestPluginOlympicChannel(unittest.TestCase):
    def test_can_handle_url(self):
        urls = (
            "https://www.olympicchannel.com/en/video/detail/stefanidi-husband-coach-krier-relationship/",
            "https://www.olympicchannel.com/en/live/",
            "https://www.olympicchannel.com/en/live/video/detail/olympic-ceremonies-channel/",
            "https://www.olympicchannel.com/de/video/detail/stefanidi-husband-coach-krier-relationship/",
            "https://www.olympicchannel.com/de/original-series/detail/body/body-season-season-1/episodes/"
            "treffen-sie-aaron-wheelz-fotheringham-den-paten-des-rollstuhl-extremsports/",
        )
        for url in urls:
            # should match
            self.assertTrue(OlympicChannel.can_handle_url(url))

        # shouldn't match
        self.assertFalse(OlympicChannel.can_handle_url("https://www.olympicchannel.com/en/"))
        self.assertFalse(OlympicChannel.can_handle_url("https://www.olympicchannel.com/en/channel/olympic-channel/"))
