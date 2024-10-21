from streamlink.plugins.tv3cat import TV3Cat
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlTV3Cat(PluginCanHandleUrl):
    __plugin__ = TV3Cat

    should_match_groups = [
        (("live", "https://www.3cat.cat/3cat/directes/tv3/"), {"ident": "tv3"}),
        (("live", "https://www.ccma.cat/3cat/directes/tv3/"), {"ident": "tv3"}),
        (("live", "https://www.ccma.cat/3cat/directes/324/"), {"ident": "324"}),
        (("live", "https://www.ccma.cat/3cat/directes/esport3/"), {"ident": "esport3"}),
        (("live", "https://www.ccma.cat/3cat/directes/sx3/"), {"ident": "sx3"}),
        (("live", "https://www.ccma.cat/3cat/directes/catalunya-radio/"), {"ident": "catalunya-radio"}),
        (
            ("vod", "https://www.3cat.cat/3cat/t1xc1-arribada/video/6260741/"),
            {"ident": "6260741"},
        ),
        (
            ("vod", "https://www.ccma.cat/3cat/t1xc1-arribada/video/6260741/"),
            {"ident": "6260741"},
        ),
        (
            ("vod", "https://www.ccma.cat/3cat/merli-els-peripatetics-capitol-1/video/5549976/"),
            {"ident": "5549976"},
        ),
        (
            ("vod", "https://www.ccma.cat/3cat/buscant-la-sostenibilitat-i-la-tecnologia-del-futur/video/6268863/"),
            {"ident": "6268863"},
        ),
    ]
