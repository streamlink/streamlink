from streamlink.plugins.nasaplus import NASAPlus
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlNASAPlus(PluginCanHandleUrl):
    __plugin__ = NASAPlus

    should_match = [
        # live / rebroadcast
        "https://plus.nasa.gov/scheduled-video/iss-expedition-70-in-flight-educational-event-with-the-creative-learning-academy-in-pensacola-florida-and-nasa-flight-engineer-jasmin-moghbeli/",
        # VOD
        "https://plus.nasa.gov/video/moon-101-introduction-to-the-moon/",
    ]
