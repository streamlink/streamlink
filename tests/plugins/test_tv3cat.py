from streamlink.plugins.tv3cat import TV3Cat
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlTV3Cat(PluginCanHandleUrl):
    __plugin__ = TV3Cat

    should_match_groups = [
        ("https://ccma.cat/tv3/directe/tv3/", {"ident": "tv3"}),
        ("https://ccma.cat/tv3/directe/324/", {"ident": "324"}),
        ("https://www.ccma.cat/tv3/directe/tv3/", {"ident": "tv3"}),
        ("https://www.ccma.cat/tv3/directe/324/", {"ident": "324"}),
    ]
