from streamlink.plugins.livespotting import LivespottingTV
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlLivespottingTV(PluginCanHandleUrl):
    __plugin__ = LivespottingTV

    should_match = [
        "https://livespotting.tv/locations?id=2mmubfyp"
    ]
