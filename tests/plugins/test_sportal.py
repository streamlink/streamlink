import unittest

from streamlink.plugins.sportal import Sportal


class TestPluginSportal(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(Sportal.can_handle_url("http://sportal.bg/sportal_live_tv.php?str=15"))
        self.assertTrue(Sportal.can_handle_url("http://www.sportal.bg/sportal_live_tv.php?"))
        self.assertTrue(Sportal.can_handle_url("http://www.sportal.bg/sportal_live_tv.php?str=15"))

        # shouldn't match
        self.assertFalse(Sportal.can_handle_url("http://www.tvcatchup.com/"))
        self.assertFalse(Sportal.can_handle_url("http://www.youtube.com/"))
