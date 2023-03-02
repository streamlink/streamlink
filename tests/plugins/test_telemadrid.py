from streamlink.plugins.telemadrid import Telemadrid
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlTelemadrid(PluginCanHandleUrl):
    __plugin__ = Telemadrid

    should_match = [
        "https://www.telemadrid.es/",
        "https://www.telemadrid.es/emision-en-directo/",
        "https://www.telemadrid.es/programas/telenoticias-1/Telenoticias-1-02032023-2-2538066218--20230302042202.html",
    ]
