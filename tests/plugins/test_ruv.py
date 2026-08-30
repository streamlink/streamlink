from streamlink.plugins.ruv import Ruv
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlRuv(PluginCanHandleUrl):
    __plugin__ = Ruv

    should_match_groups = [
        (("live", "https://www.ruv.is/sjonvarp/beint/ruv"), {"channel": "ruv"}),
        (("live", "https://www.ruv.is/sjonvarp/beint/ruv2"), {"channel": "ruv2"}),
        (("live", "https://www.ruv.is/utvarp/beint/ras1"), {"channel": "ras1"}),
        (("live", "https://www.ruv.is/utvarp/beint/ras2"), {"channel": "ras2"}),
        (("vod", "https://www.ruv.is/sjonvarp/spila/vedur/30766/agcf5m"), {"id": "30766", "episode": "agcf5m"}),
        (("vod", "https://www.ruv.is/sjonvarp/spila/kastljos/35422/ahpu2g"), {"id": "35422", "episode": "ahpu2g"}),
        (("vod", "https://www.ruv.is/utvarp/spila/laesi/37102/b1qk71"), {"id": "37102", "episode": "b1qk71"}),
    ]
