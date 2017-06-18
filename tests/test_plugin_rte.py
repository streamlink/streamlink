import unittest

from streamlink.plugins.rte import RTE


class TestPluginRTE(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(RTE.can_handle_url("http://www.rte.ie/player/99/live/8/"))
        self.assertTrue(RTE.can_handle_url("http://www.rte.ie/player/99/live/10/"))
        self.assertTrue(RTE.can_handle_url("http://www.rte.ie/player/99/live/6/"))
        self.assertTrue(RTE.can_handle_url("http://www.rte.ie/player/99/live/7/"))

        self.assertTrue(RTE.can_handle_url("http://www.rte.ie/player/99/show/rte-news-one-oclock-30003248/10714679/"))
        self.assertTrue(RTE.can_handle_url("http://www.rte.ie/player/99/show/the-ray-darcy-show-extras-30003588/10714469/"))
        self.assertTrue(RTE.can_handle_url("http://www.rte.ie/player/99/show/lotto-1251/10714463/"))

        # shouldn't match
        self.assertFalse(RTE.can_handle_url("http://www.rte.ie/"))
        self.assertFalse(RTE.can_handle_url("http://www.rte.ie/tv/"))
        self.assertFalse(RTE.can_handle_url("http://www.rte.ie/player/"))
        self.assertFalse(RTE.can_handle_url("http://www.tvcatchup.com/"))
        self.assertFalse(RTE.can_handle_url("http://www.youtube.com/"))
