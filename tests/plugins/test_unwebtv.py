from streamlink.plugins.unwebtv import UNWebTV
from tests.plugins import PluginCanHandleUrl


class TestPluginUNWebTV(PluginCanHandleUrl):
    __plugin__ = UNWebTV

    should_match = [
        "https://webtv.un.org/",
        "http://webtv.un.org/",
        "https://webtv.un.org/en",
        "https://webtv.un.org/en/asset/k14/k143ucuid9",
        "https://webtv.un.org/fr/asset/k1x/k1x2345",
        "https://webtv.un.org/es/asset/k1y/k1y6789",
        # Some URLs might have query parameters
        "https://webtv.un.org/en?foo=bar",
    ]

    should_not_match = [
        "https://www.un.org/",
        "https://media.un.org/",
        "https://webtv.other.org/",
    ]
