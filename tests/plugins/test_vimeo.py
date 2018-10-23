import unittest

from streamlink.plugins.vimeo import Vimeo


class TestPluginVimeo(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(Vimeo.can_handle_url("https://vimeo.com/237163735"))
        self.assertTrue(Vimeo.can_handle_url("https://vimeo.com/channels/music/176894130"))
        self.assertTrue(Vimeo.can_handle_url("https://vimeo.com/album/3706071/video/148903960"))
        self.assertTrue(Vimeo.can_handle_url("https://vimeo.com/ondemand/surveyopenspace/92630739"))
        self.assertTrue(Vimeo.can_handle_url("https://vimeo.com/ondemand/100footsurfingdays"))
        self.assertTrue(Vimeo.can_handle_url("https://player.vimeo.com/video/176894130"))

        # shouldn't match
        self.assertFalse(Vimeo.can_handle_url("https://www.vimeo.com/"))
        self.assertFalse(Vimeo.can_handle_url("http://www.tvcatchup.com/"))
        self.assertFalse(Vimeo.can_handle_url("http://www.youtube.com/"))
