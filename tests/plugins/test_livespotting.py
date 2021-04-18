from streamlink.plugins.livespotting import LivespottingTV
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlLivespottingTV(PluginCanHandleUrl):
    __plugin__ = LivespottingTV

    should_match = [
        "https://livespotting.tv/locations?id=2mmubfyp",
        "https://livespotting.tv/deutschland/bad-zwischenahn/i4gpp4ev",
        "https://livespotting.tv/deutschland/land/2mmubfyp",
    ]
