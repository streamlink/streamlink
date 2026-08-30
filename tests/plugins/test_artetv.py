from streamlink.plugins.artetv import ArteTV
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlArteTV(PluginCanHandleUrl):
    __plugin__ = ArteTV

    should_match_groups = [
        # live
        (
            ("live", "https://www.arte.tv/fr/direct"),
            {"language": "fr"},
        ),
        (
            ("live", "https://www.arte.tv/fr/direct/"),
            {"language": "fr"},
        ),
        (
            ("live", "https://www.arte.tv/de/live"),
            {"language": "de"},
        ),
        (
            ("live", "https://www.arte.tv/de/live/"),
            {"language": "de"},
        ),
        # vod
        (
            ("vod", "https://www.arte.tv/de/videos/097372-001-A/mysterium-satoshi-bitcoin-wie-alles-begann-1-6/"),
            {"language": "de", "video_id": "097372-001-A"},
        ),
        (
            ("vod", "https://www.arte.tv/en/videos/097372-001-A/the-satoshi-mystery-the-story-of-bitcoin/"),
            {"language": "en", "video_id": "097372-001-A"},
        ),
        # old vod URLs with redirects
        (
            ("vod", "https://www.arte.tv/guide/de/097372-001-A/mysterium-satoshi-bitcoin-wie-alles-begann-1-6/"),
            {"language": "de", "video_id": "097372-001-A"},
        ),
        (
            ("vod", "https://www.arte.tv/guide/en/097372-001-A/the-satoshi-mystery-the-story-of-bitcoin/"),
            {"language": "en", "video_id": "097372-001-A"},
        ),
    ]

    should_not_match = [
        "https://www.arte.tv/guide/de/live/",
        "https://www.arte.tv/guide/fr/plus7/",
        "https://www.arte.tv/guide/de/plus7/",
        # shouldn't match - playlists without video ids in url
        "https://www.arte.tv/en/videos/RC-014457/the-power-of-forests/",
        "https://www.arte.tv/en/videos/RC-013118/street-art/",
    ]
