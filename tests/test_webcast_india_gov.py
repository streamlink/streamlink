import unittest

from streamlink.plugins.webcast_india_gov import WebcastIndiaGov


class TestPluginWebcastIndiaGov(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(WebcastIndiaGov.can_handle_url("http://webcast.gov.in/ddpunjabi/"))
        self.assertTrue(WebcastIndiaGov.can_handle_url("http://webcast.gov.in/#Channel1"))
        self.assertTrue(WebcastIndiaGov.can_handle_url("http://webcast.gov.in/#Channel3"))

        # shouldn't match
        self.assertFalse(WebcastIndiaGov.can_handle_url("http://meity.gov.in/"))
        self.assertFalse(WebcastIndiaGov.can_handle_url("http://www.nic.in/"))
        self.assertFalse(WebcastIndiaGov.can_handle_url("http://digitalindiaawards.gov.in/"))
