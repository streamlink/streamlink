from streamlink.plugins.gardenersworld import GardenersWorld
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlGardenersWorld(PluginCanHandleUrl):
    __plugin__ = GardenersWorld

    should_match = [
        'http://www.gardenersworld.com/',
    ]
