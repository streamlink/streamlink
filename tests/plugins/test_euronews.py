from streamlink.plugins.euronews import Euronews
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlEuronews(PluginCanHandleUrl):
    __plugin__ = Euronews

    should_match = [
        "http://www.euronews.com/live",
        "http://fr.euronews.com/live",
        "http://de.euronews.com/live",
        "http://it.euronews.com/live",
        "http://es.euronews.com/live",
        "http://pt.euronews.com/live",
        "http://ru.euronews.com/live",
        "http://ua.euronews.com/live",
        "http://tr.euronews.com/live",
        "http://gr.euronews.com/live",
        "http://hu.euronews.com/live",
        "http://fa.euronews.com/live",
        "http://arabic.euronews.com/live",
        "http://www.euronews.com/2017/05/10/peugeot-expects-more-opel-losses-this-year",
        "http://fr.euronews.com/2017/05/10/l-ag-de-psa-approuve-le-rachat-d-opel"
    ]
