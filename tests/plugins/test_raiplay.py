from streamlink.plugins.raiplay import RaiPlay
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlRaiPlay(PluginCanHandleUrl):
    __plugin__ = RaiPlay

    should_match = [
        "http://www.raiplay.it/dirette/rai1",
        "http://www.raiplay.it/dirette/rai2",
        "http://www.raiplay.it/dirette/rai3",
        "http://raiplay.it/dirette/rai3",
        "https://raiplay.it/dirette/rai3",
        "http://www.raiplay.it/dirette/rainews24",
        "https://www.raiplay.it/dirette/rainews24",
    ]
