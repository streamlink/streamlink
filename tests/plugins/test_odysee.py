from streamlink.plugins.odysee import Odysee
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlOdysee(PluginCanHandleUrl):
    __plugin__ = Odysee

    should_match = [
        "https://odysee.com/@Odysee:8/Odysee-Land:1",
        "https://odysee.com/@Odysee:8/YouTube-Casting-Couch:9",
        "https://www.odysee.com/@Odysee:8/YouTube-Casting-Couch:9",
        "https://odysee.com/@Odysee:8/call-an-ambulance:6",
        "https://odysee.com/@Odysee:8/Odysee-Zuckerborg:4",
    ]

    should_not_match = [
        "https://odysee.com/$/education",
        "https://odysee.com/$/lifestyle",
    ]
