from streamlink.plugins.tvkaista import TVKaista
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlTVKaista(PluginCanHandleUrl):
    __plugin__ = TVKaista

    should_match_groups = [
        (
            ("live", "https://www.tvkaista.org/mtv3/suora"),
            {"channel": "mtv3"},
        ),
        (
            ("live", "https://tvkaista.org/yle-tv1/suora"),
            {"channel": "yle-tv1"},
        ),
        (
            ("live", "https://www.tvkaista.org/sub/suora"),
            {"channel": "sub"},
        ),
    ]

    should_not_match = [
        "https://www.tvkaista.org/",
        "https://www.tvkaista.org/mtv3",
        "https://www.tvkaista.org/login",
        "https://www.tvkaista.org/mtv3/suora/extra",
    ]
