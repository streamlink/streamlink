import unittest

from streamlink.plugins.rtbf import RTBF


class TestPluginRTBF(unittest.TestCase):
    def test_can_handle_url(self):
        # should match
        self.assertTrue(RTBF.can_handle_url("https://www.rtbf.be/auvio/direct_doc-shot?lid=122046#/"))
        self.assertTrue(RTBF.can_handle_url("https://www.rtbf.be/auvio/emissions/detail_dans-la-toile?id=11493"))
        self.assertTrue(RTBF.can_handle_url("http://www.rtbfradioplayer.be/radio/liveradio/purefm"))

        # shouldn't match
        self.assertFalse(RTBF.can_handle_url("http://www.rtbf.be/"))
        self.assertFalse(RTBF.can_handle_url("http://www.rtbf.be/auvio"))
        self.assertFalse(RTBF.can_handle_url("http://www.rtbfradioplayer.be/"))
        self.assertFalse(RTBF.can_handle_url("http://www.tvcatchup.com/"))
        self.assertFalse(RTBF.can_handle_url("http://www.youtube.com/"))
