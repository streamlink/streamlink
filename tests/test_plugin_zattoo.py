import unittest

from streamlink.plugins.zattoo import Zattoo


class TestPluginZattoo(unittest.TestCase):
    def test_can_handle_url(self):
        # ewe live
        self.assertTrue(Zattoo.can_handle_url('http://tvonline.ewe.de/watch/daserste'))
        self.assertTrue(Zattoo.can_handle_url('http://tvonline.ewe.de/watch/zdf'))
        # netcologne live
        self.assertTrue(Zattoo.can_handle_url('https://nettv.netcologne.de/watch/daserste'))
        self.assertTrue(Zattoo.can_handle_url('https://nettv.netcologne.de/watch/zdf'))
        # zattoo live
        self.assertTrue(Zattoo.can_handle_url('https://zattoo.com/watch/daserste'))
        self.assertTrue(Zattoo.can_handle_url('https://zattoo.com/watch/zdf'))
        # zattoo vod
        self.assertTrue(Zattoo.can_handle_url('https://zattoo.com/ondemand/watch/ibR2fpisWFZGvmPBRaKnFnuT-alarm-am-airport'))
        self.assertTrue(Zattoo.can_handle_url('https://zattoo.com/ondemand/watch/G8S7JxcewY2jEwAgMzvFWK8c-berliner-schnauzen'))
        # zattoo recording
        self.assertTrue(Zattoo.can_handle_url('https://zattoo.com/ondemand/watch/srf_zwei/110223896-die-schweizermacher/52845783/1455130800000/1455137700000/6900000'))
        self.assertTrue(Zattoo.can_handle_url('https://zattoo.com/watch/tve/130920738-viaje-al-centro-de-la-tele/96847859/1508777100000/1508779800000/0'))

        # shouldn't match
        self.assertFalse(Zattoo.can_handle_url('https://ewe.de'))
        self.assertFalse(Zattoo.can_handle_url('https://netcologne.de'))
        self.assertFalse(Zattoo.can_handle_url('https://zattoo.com'))
