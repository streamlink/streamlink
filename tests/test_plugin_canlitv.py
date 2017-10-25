import unittest

from streamlink.plugins.canlitv import Canlitv, _m3u8_re


class TestPluginCanlitv(unittest.TestCase):
    def test_m3u8_re(self):
        def test_re(text):
            m = _m3u8_re.search(text)
            self.assertTrue(m and len(m.group("url")) > 0)

        test_re('file: "test" ')
        test_re('file:"test"')
        test_re('file : "test"')
        test_re('file   :   "test"  ')
        test_re("file: 'test'")
        test_re("file :'test'")
        test_re("file : 'test'")
        test_re("file   :   'test'")

    def test_can_handle_url(self):
        # should match
        self.assertTrue(Canlitv.can_handle_url("http://www.canlitv.plus/channel"))
        self.assertTrue(Canlitv.can_handle_url("http://www.canlitv.com/channel"))
        self.assertTrue(Canlitv.can_handle_url("http://www.canlitvlive.co/izle/channel.html"))
        self.assertTrue(Canlitv.can_handle_url("http://www.canlitvlive.live/izle/channel.html"))
        self.assertTrue(Canlitv.can_handle_url("http://www.canlitvlive.io/izle/channel.html"))
        self.assertTrue(Canlitv.can_handle_url("http://www.canlitvlive.site/izle/channel.html"))
        self.assertTrue(Canlitv.can_handle_url("http://www.ecanlitvizle.net/channel/"))
        self.assertTrue(Canlitv.can_handle_url("http://www.ecanlitvizle.net/onizleme.php?kanal=channel"))
        self.assertTrue(Canlitv.can_handle_url("http://www.ecanlitvizle.net/tv.php?kanal=channel"))
        # shouldn't match
        self.assertFalse(Canlitv.can_handle_url("http://www.canlitv.com"))
        self.assertFalse(Canlitv.can_handle_url("http://www.canlitv.plus"))
        self.assertFalse(Canlitv.can_handle_url("http://www.ecanlitvizle.net"))
        self.assertFalse(Canlitv.can_handle_url("http://www.canlitvlive.co"))
        self.assertFalse(Canlitv.can_handle_url("http://www.canlitvlive.live"))
        self.assertFalse(Canlitv.can_handle_url("http://www.canlitvlive.io"))
        self.assertFalse(Canlitv.can_handle_url("http://www.canlitvlive.site"))
        self.assertFalse(Canlitv.can_handle_url("http://www.ecanlitvizle.net"))

