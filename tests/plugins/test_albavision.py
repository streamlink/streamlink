from streamlink.plugins.albavision import Albavision
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlAlbavision(PluginCanHandleUrl):
    __plugin__ = Albavision

    should_match_groups = [
        (("antena7", "https://antena7.com.do/envivo-canal-7/"), {}),
        (("antena7", "https://www.antena7.com.do/envivo-canal7"), {}),
        (("antena7", "https://www.antena7.com.do/envivo-canal7/"), {}),
        (("antena7", "https://www.antena7.com.do/envivo-canal7#"), {}),
        (("antena7", "https://www.antena7.com.do/envivo-canal-7#"), {}),
        (("antena7", "https://www.antena7.com.do/en-vivo-canal-99/"), {}),
        (("antena7", "https://www.antena7.com.do/en-vivo-canal-99#"), {}),
        (("antena7", "https://www.antena7.com.do/envivo-canal-7/"), {}),
        (("antena7", "https://www.antena7.com.do/envivo-canal-21/"), {}),
        (("atv", "https://www.atv.pe/envivo-atv"), {}),
        (("atv", "https://www.atv.pe/envivo-atvmas"), {}),
        (("c9n", "https://www.c9n.com.py/envivo/"), {}),
        (("canal10", "https://www.canal10.com.ni/envivo/"), {}),
        (("canal12", "https://www.canal12.com.sv/envivo/"), {}),
        (("chapintv", "https://www.chapintv.com/envivo-canal-3/"), {}),
        (("chapintv", "https://www.chapintv.com/envivo-canal-7/"), {}),
        (("chapintv", "https://www.chapintv.com/envivo-canal-23/"), {}),
        (("elnueve", "https://www.elnueve.com.ar/en-vivo/"), {}),
        (("redbolivision", "https://www.redbolivision.tv.bo/envivo-canal-5/"), {}),
        (("redbolivision", "https://www.redbolivision.tv.bo/upptv/"), {}),
        (("repretel", "https://www.repretel.com/envivo-canal2/"), {}),
        (("repretel", "https://www.repretel.com/envivo-canal4/"), {}),
        (("repretel", "https://www.repretel.com/envivo-canal6/"), {}),
        (("repretel", "https://www.repretel.com/en-vivo-canal-11/"), {}),
        (("rts", "https://www.rts.com.ec/envivo/"), {}),
        (("snt", "https://www.snt.com.py/envivo/"), {}),
        (("tvc", "https://www.tvc.com.ec/envivo/"), {}),
        (("vtv", "https://www.vtv.com.hn/envivo/"), {}),
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
