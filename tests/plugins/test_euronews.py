from streamlink.plugins.euronews import Euronews
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlEuronews(PluginCanHandleUrl):
    __plugin__ = Euronews

    should_match = [
        "https://www.euronews.com/live",
        "https://fr.euronews.com/live",
        "https://de.euronews.com/live",
        "https://it.euronews.com/live",
        "https://es.euronews.com/live",
        "https://pt.euronews.com/live",
        "https://ru.euronews.com/live",
        "https://ua.euronews.com/live",
        "https://tr.euronews.com/live",
        "https://gr.euronews.com/live",
        "https://hu.euronews.com/live",
        "https://fa.euronews.com/live",
        "https://arabic.euronews.com/live",
        "https://www.euronews.com/video",
        "https://www.euronews.com/2023/01/02/giving-europe-a-voice-television-news-network-euronews-turns-30",
    ]
