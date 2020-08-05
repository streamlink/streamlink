import unittest

from streamlink.plugins.mrtmk import MRTmk

class TestPluginBigo(unittest.TestCase):
  def test_can_handle_url(self)
    # should match
    self.assertTrue(MRTmk.can_handle_url("http://play.mrt.com.mk/live/658323455489957"))
    self.assertTrue(MRTmk.can_handle_url("http://play.mrt.com.mk/live/47"))
    self.assertTrue(MRTmk.can_handle_url("http://play.mrt.com.mk/play/1581"))

    #shouldn't match
    self.assertFalse(IDF1.can_handle_url("http://play.mrt.com.mk/"))
    self.assertFalse(IDF1.can_handle_url("http://play.mrt.com.mk/c/2"))
    self.assertFalse(IDF1.can_handle_url("http://www.tvcatchup.com/"))
    self.assertFalse(IDF1.can_handle_url("http://www.youtube.com/"))
