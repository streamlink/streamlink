from streamlink.plugins.skylinewebcams import SkylineWebcams
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlSkylineWebcams(PluginCanHandleUrl):
    __plugin__ = SkylineWebcams

    should_match = [
        "https://www.skylinewebcams.com/de/webcam/norge/nordland/lofoten/henningsvaer.html",
    ]

    should_not_match = [
        "https://www.skylinewebcams.com/de/webcam/thailand/central-thailand.html",
    ]
