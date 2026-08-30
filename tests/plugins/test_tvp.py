from streamlink.plugins.tvp import TVP
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlTVP(PluginCanHandleUrl):
    __plugin__ = TVP

    should_match_groups = [
        # live
        (
            ("live", "https://vod.tvp.pl/live,1/tvp-info,399699/2025-05-20/serwis-info-dzien,2086908"),
            {"channel_id": "399699", "show_id": "2086908"},
        ),
        (
            ("live", "https://vod.tvp.pl/live,1/tvp-world,399731/2025-05-20/interview-from-vilnius---ep-146,2088070"),
            {"channel_id": "399731", "show_id": "2088070"},
        ),
        # VOD
        (
            ("vod", "https://vod.tvp.pl/filmy-fabularne,136/podroz-ksiecia,852411"),
            {"vod_id": "852411"},
        ),
        (
            ("vod", "https://vod.tvp.pl/filmy-fabularne,136/bambi-opowiesc-lesna,2053604"),
            {"vod_id": "2053604"},
        ),
        # VOD episode
        (
            ("vod", "https://vod.tvp.pl/seriale,18/dzikie-korytarze-odcinki,2092682/odcinek-1,S01E01,2092684"),
            {"vod_id": "2092684"},
        ),
        # tvp.info
        (
            (
                "tvp_info",
                "https://www.tvp.info/ogladaj-na-zywo",
            ),
            {},
        ),
        (
            (
                "tvp_info",
                "https://www.tvp.info/86792059/kot-przemytnik-utknal-na-wieziennym-ogrodzeniu",
            ),
            {},
        ),
        # sport.tvp
        (
            (
                "tvp_sport",
                "https://sport.tvp.pl/86453177/snooker-polska-liga-snookera-top16-polfinal-i-final-zapis",
            ),
            {"stream_id": "86453177"},
        ),
    ]

    should_not_match = [
        "https://tvp.pl/",
        "https://stream.tvp.pl/",
        "https://vod.tvp.pl/",
        "https://tvpstream.vod.tvp.pl/",
    ]
