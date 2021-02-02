from streamlink.plugins.gulli import Gulli
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlGulli(PluginCanHandleUrl):
    __plugin__ = Gulli

    should_match = [
        "http://replay.gulli.fr/Direct",
        "http://replay.gulli.fr/dessins-animes/My-Little-Pony-les-amies-c-est-magique/VOD68328764799000",
        "https://replay.gulli.fr/emissions/In-Ze-Boite2/VOD68639028668000",
        "https://replay.gulli.fr/series/Power-Rangers-Dino-Super-Charge/VOD68612908435000"
    ]

    should_not_match = [
        "http://replay.gulli.fr/",
        "http://replay.gulli.fr/dessins-animes",
        "http://replay.gulli.fr/emissions",
        "http://replay.gulli.fr/series",
    ]
