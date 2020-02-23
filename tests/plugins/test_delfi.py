import unittest

from streamlink.plugins.delfi import Delfi


class TestPluginDelfi(unittest.TestCase):
    def test_can_handle_url(self):
        should_match = [
            "http://www.delfi.lt/video/sportas/kroatiska-tvarka-kaliningrade-laisvai-liejosi-gerimai-dainos"
            + "-sokiai-ir-ziezirbos.d?id=78322857",
            "https://www.delfi.lt/video/sportas/zalgiris-atsidure-per-pergale-nuo-lkl-aukso.d?id=78321125",
            "https://www.delfi.lt/video/laidos/nba/warriors-cempioniskomis-tapusios-ketvirtos-finalo"
            + "-rungtynes.d?id=78246059",
            "http://rahvahaal.delfi.ee/news/videod/video-joviaalne-piduline-kaotab-raekoja-platsil-ilutulestiku"
            + "-ule-kontrolli-ja-raketid-lendavad-rahva-sekka?id=82681069",
            "http://www.delfi.lv/delfi-tv-ar-jani-domburu/pilnie-raidijumi/delfi-tv-ar-jani-domburu-atbild"
            + "-veselibas-ministre-anda-caksa-pilna-intervija?id=49515013"
        ]
        for url in should_match:
            self.assertTrue(Delfi.can_handle_url(url))

        should_not_match = [
            "http://www.tvcatchup.com/",
            "http://www.youtube.com/"
        ]
        for url in should_not_match:
            self.assertFalse(Delfi.can_handle_url(url))
