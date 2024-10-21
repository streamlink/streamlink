from streamlink.plugins.raiplay import RaiPlay
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlRaiPlay(PluginCanHandleUrl):
    __plugin__ = RaiPlay

    should_match = [
        ("live", "https://raiplay.it/dirette/rai1"),
        ("live", "https://www.raiplay.it/dirette/rai1"),
        ("live", "https://www.raiplay.it/dirette/rai2"),
        ("live", "https://www.raiplay.it/dirette/rai3"),
        ("live", "https://www.raiplay.it/dirette/rainews24"),
        (
            "vod",
            "https://raiplay.it/video/2023/11/Un-posto-al-sole---Puntata-del-08112023-EP6313-1377bcf9-db3f-40f7-aa05-fefeb086ec68.html",
        ),
        (
            "vod",
            "https://www.raiplay.it/video/2023/11/Un-posto-al-sole---Puntata-del-08112023-EP6313-1377bcf9-db3f-40f7-aa05-fefeb086ec68.html",
        ),
    ]
