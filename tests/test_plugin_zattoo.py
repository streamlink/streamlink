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

        # shouldn't match
        self.assertFalse(Zattoo.can_handle_url('https://ewe.de'))
        self.assertFalse(Zattoo.can_handle_url('https://netcologne.de'))
        self.assertFalse(Zattoo.can_handle_url('https://zattoo.com'))
