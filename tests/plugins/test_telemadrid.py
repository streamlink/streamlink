from streamlink.plugins.telemadrid import Telemadrid
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlTelemadrid(PluginCanHandleUrl):
    __plugin__ = Telemadrid

    should_match = [
        "https://www.telemadrid.es/",
        "https://www.telemadrid.es/emision-en-directo/",
    ]
