import unittest

from streamlink import Streamlink
from streamlink.plugins.delfi import Delfi


class TestPluginDelfi(unittest.TestCase):
    def setUp(self):
        self.session = Streamlink()

    def test_can_handle_url(self):
        # should match
        self.assertTrue(Delfi.can_handle_url("http://www.delfi.lt/video/sportas/kroatiska-tvarka-kaliningrade-laisvai-liejosi-gerimai-dainos-sokiai-ir-ziezirbos.d?id=78322857"))
        self.assertTrue(Delfi.can_handle_url("https://www.delfi.lt/video/sportas/zalgiris-atsidure-per-pergale-nuo-lkl-aukso.d?id=78321125"))
        self.assertTrue(Delfi.can_handle_url("https://www.delfi.lt/video/laidos/nba/warriors-cempioniskomis-tapusios-ketvirtos-finalo-rungtynes.d?id=78246059"))
        self.assertTrue(Delfi.can_handle_url("http://rahvahaal.delfi.ee/news/videod/video-joviaalne-piduline-kaotab-raekoja-platsil-ilutulestiku-ule-kontrolli-ja-raketid-lendavad-rahva-sekka?id=82681069"))
        self.assertTrue(Delfi.can_handle_url("http://www.delfi.lv/delfi-tv-ar-jani-domburu/pilnie-raidijumi/delfi-tv-ar-jani-domburu-atbild-veselibas-ministre-anda-caksa-pilna-intervija?id=49515013"))

    def test_can_handle_url_negative(self):
        # shouldn't match
        self.assertFalse(Delfi.can_handle_url("http://www.tvcatchup.com/"))
        self.assertFalse(Delfi.can_handle_url("http://www.youtube.com/"))
