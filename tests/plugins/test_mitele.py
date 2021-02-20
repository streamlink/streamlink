from streamlink.plugins.mitele import Mitele
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlMitele(PluginCanHandleUrl):
    __plugin__ = Mitele

    should_match = [
        "http://www.mitele.es/directo/bemad",
        "http://www.mitele.es/directo/boing",
        "http://www.mitele.es/directo/cuatro",
        "http://www.mitele.es/directo/divinity",
        "http://www.mitele.es/directo/energy",
        "http://www.mitele.es/directo/fdf",
        "http://www.mitele.es/directo/telecinco",
        "https://www.mitele.es/directo/gh-duo-24h-senal-1",
        "https://www.mitele.es/directo/gh-duo-24h-senal-2",
    ]

    should_not_match = [
        "http://www.mitele.es",
    ]
