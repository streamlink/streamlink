from streamlink.plugins.gulli import Gulli
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlGulli(PluginCanHandleUrl):
    __plugin__ = Gulli

    should_match = [
        (
            "live",
            "https://replay.gulli.fr/Direct",
        ),
        (
            "vod",
            "https://replay.gulli.fr/dessins-animes/Bob-l-eponge-s10/bob-l-eponge-s10-e05-un-bon-gros-dodo-vod69736581475000",
        ),
        (
            "vod",
            "https://replay.gulli.fr/emissions/Animaux-VIP-une-bete-de-reno-s02/animaux-vip-une-bete-de-reno-s02-e09-la-taniere-du-dragon-vod69634261609000",
        ),
        (
            "vod",
            "https://replay.gulli.fr/series/Black-Panther-Dangers-au-Wakanda/black-panther-dangers-au-wakanda-black-panther-dangers-au-wakanda-vod69941412154000",
        ),
    ]

    should_not_match = [
        "http://replay.gulli.fr/",
        "http://replay.gulli.fr/dessins-animes",
        "http://replay.gulli.fr/emissions",
        "http://replay.gulli.fr/series",
    ]
