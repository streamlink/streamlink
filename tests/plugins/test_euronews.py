from streamlink.plugins.euronews import Euronews
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlEuronews(PluginCanHandleUrl):
    __plugin__ = Euronews

    should_match_groups = [
        (("live", "https://euronews.com/live"), {}),
        (("live", "https://www.euronews.com/live"), {"subdomain": "www"}),
        (("live", "https://fr.euronews.com/live"), {"subdomain": "fr"}),
        (("live", "https://de.euronews.com/live"), {"subdomain": "de"}),
        (("live", "https://it.euronews.com/live"), {"subdomain": "it"}),
        (("live", "https://es.euronews.com/live"), {"subdomain": "es"}),
        (("live", "https://pt.euronews.com/live"), {"subdomain": "pt"}),
        (("live", "https://ru.euronews.com/live"), {"subdomain": "ru"}),
        (("live", "https://tr.euronews.com/live"), {"subdomain": "tr"}),
        (("live", "https://gr.euronews.com/live"), {"subdomain": "gr"}),
        (("live", "https://hu.euronews.com/live"), {"subdomain": "hu"}),
        (("live", "https://fa.euronews.com/live"), {"subdomain": "fa"}),
        (("live", "https://arabic.euronews.com/live"), {"subdomain": "arabic"}),
        (
            ("vod", "https://www.euronews.com/video/2025/02/28/latest-news-bulletin-february-28th-midday"),
            {},
        ),
        (
            ("vod", "https://www.euronews.com/my-europe/2025/02/25/whats-at-stake-for-europe-after-the-german-election"),
            {},
        ),
        (
            ("vod", "https://de.euronews.com/my-europe/2025/02/24/frankreichs-prasident-macron-wird-trump-treffen"),
            {},
        ),
    ]

    should_not_match = [
        "https://euronews.com/",
        "https://www.euronews.com/",
    ]
