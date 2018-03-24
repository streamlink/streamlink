import unittest

from streamlink.plugins.radio2see import Radio2See


class TestPluginRadio2See(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(Radio2See.can_handle_url("http:/www.radio21.de/tv/"))
        self.assertTrue(Radio2See.can_handle_url("http:/www.radio21.de/musik/tv/"))
        self.assertTrue(Radio2See.can_handle_url("http:/www.rockland.de/tv/"))
        self.assertTrue(Radio2See.can_handle_url("http:/www.rockland.de/musik/tv/"))

        # shouldn't match
        self.assertFalse(Radio2See.can_handle_url("http:/www.radio21.de/"))
        self.assertFalse(Radio2See.can_handle_url("http:/www.rockland.de/"))
