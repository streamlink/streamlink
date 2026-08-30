from streamlink.plugins.earthcam import EarthCam
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlEarthCam(PluginCanHandleUrl):
    __plugin__ = EarthCam

    should_match = [
        "https://www.earthcam.com/usa/newyork/timessquare/?cam=tsstreet",
        "https://www.earthcam.com/usa/newyork/timessquare/?cam=gts1",
    ]
