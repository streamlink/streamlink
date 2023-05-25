from streamlink.plugins.albavision import Albavision
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlAlbavision(PluginCanHandleUrl):
    __plugin__ = Albavision

    should_match = [
        "http://antena7.com.do/envivo-canal-7/",
        "http://www.antena7.com.do/envivo-canal-7/",
        "https://antena7.com.do/envivo-canal-7/",
        "https://www.antena7.com.do/envivo-canal7",
        "https://www.antena7.com.do/envivo-canal7/",
        "https://www.antena7.com.do/envivo-canal7#",
        "https://www.antena7.com.do/envivo-canal-7#",
        "https://www.antena7.com.do/en-vivo-canal-99/",
        "https://www.antena7.com.do/en-vivo-canal-99#",
        # All channel URLs from supported sites
        "https://www.antena7.com.do/envivo-canal-7/",
        "https://www.antena7.com.do/envivo-canal-21/",
        "https://www.atv.pe/envivo-atv",
        "https://www.atv.pe/envivo-atvmas",
        "https://www.c9n.com.py/envivo/",
        "https://www.canal10.com.ni/envivo/",
        "https://www.canal12.com.sv/envivo/",
        "https://www.chapintv.com/envivo-canal-3/",
        "https://www.chapintv.com/envivo-canal-7/",
        "https://www.chapintv.com/envivo-canal-23/",
        "https://www.elnueve.com.ar/en-vivo/",
        "https://www.redbolivision.tv.bo/envivo-canal-5/",
        "https://www.redbolivision.tv.bo/upptv/",
        "https://www.repretel.com/envivo-canal2/",
        "https://www.repretel.com/envivo-canal4/",
        "https://www.repretel.com/envivo-canal6/",
        "https://www.repretel.com/en-vivo-canal-11/",
        "https://www.rts.com.ec/envivo/",
        "https://www.snt.com.py/envivo/",
        "https://www.tvc.com.ec/envivo/",
        "https://www.vtv.com.hn/envivo/",
    ]
    should_not_match = [
        "https://fake.antena7.com.do/envivo-canal-7/",
        "https://www.antena7.com.do/envivo-canal123",
        "https://www.antena7.com.do/envivo-canal123/",
        "https://www.antena7.com.do/envivo-canal-123",
        "https://www.antena7.com.do/envivo-canal-123/",
        "https://www.antena7.com.do/envivo-canal-123#",
        "https://www.antena7.com.do/envivo-canalabc",
        "https://www.antena7.com.do/envivo-canal-abc",
        "https://www.antena7.com.do/envivo-canal-7/extra",
        "https://www.antena7.com.do/envivo-canal-7#extra",
        "https://www.antena7.com.do/something",
    ]


class TestPluginAlbavision:
    def test_transform(self):
        token = Albavision.transform_token("6b425761cc8a86569b1a05a9bf1870c95fca717dOK", 436171)
        assert token == "6b425761cc8a86569b1a05a9bf1870c95fca717d"
