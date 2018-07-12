import unittest

from streamlink.plugins.lrt import LRT


class TestPluginLRT(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            "https://www.lrt.lt/mediateka/tiesiogiai/lrt-televizija",
            "https://www.lrt.lt/mediateka/tiesiogiai/lrt-kultura",
            "https://www.lrt.lt/mediateka/tiesiogiai/lrt-lituanica"
            "https://www.lrt.lt/mediateka/irasas/1013694276/savanoriai-tures-galimybe-pamatyti-popieziu-is-arciau#wowzaplaystart=1511000&wowzaplayduration=168000"
        ]
        for url in should_match:
            self.assertTrue(LRT.can_handle_url(url))

    def test_can_handle_url_negative(self):
        should_not_match = [
            "https://www.lrt.lt",
            "https://www.youtube.com",

        ]
        for url in should_not_match:
            self.assertFalse(LRT.can_handle_url(url))
