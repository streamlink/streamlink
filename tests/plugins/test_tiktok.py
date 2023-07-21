from streamlink.plugins.tiktok import TikTok
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlTikTok(PluginCanHandleUrl):
    __plugin__ = TikTok

    should_match = [
        "https://www.tiktok.com/@kbc_news/live",
        "https://www.tiktok.com/@hiroshima_tssnews/live",
        "https://www.tiktok.com/@tv_asahi_news/live",
        "https://www.tiktok.com/@noticiascaracol/live",
        "https://www.tiktok.com/@tv_asahi_news/live",
    ]

    should_not_match = [
        "https://www.tiktok.com/@kbc_news",
        "https://www.tiktok.com/@hiroshima_tssnews",
        "https://www.tiktok.com/@tv_asahi_news",
        "https://www.tiktok.com/@noticiascaracol",
        "https://www.tiktok.com/@tv_asahi_news",
    ]
