from streamlink.plugins.stadium import Stadium
import unittest


class TestPluginStadium(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(Stadium.can_handle_url("http://www.watchstadium.com/live"))
        self.assertTrue(Stadium.can_handle_url("https://www.watchstadium.com/live"))
        self.assertTrue(Stadium.can_handle_url("https://watchstadium.com/live"))
        self.assertTrue(Stadium.can_handle_url("http://watchstadium.com/live"))

        # shouldn't match
        self.assertFalse(Stadium.can_handle_url("http://www.watchstadium.com/anything/else"))
        self.assertFalse(Stadium.can_handle_url("http://www.tvcatchup.com/"))
        self.assertFalse(Stadium.can_handle_url("http://www.youtube.com/"))
