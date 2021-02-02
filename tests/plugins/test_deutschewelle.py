from streamlink.plugins.deutschewelle import DeutscheWelle
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlDeutscheWelle(PluginCanHandleUrl):
    __plugin__ = DeutscheWelle

    should_match = [
        "http://www.dw.com/en/media-center/live-tv/s-100825",
        "http://www.dw.com/fr/médiathèque/direct-tv/s-100948?channel=5",
        "http://www.dw.com/de/tim-bendzko-deutsch-pop-darling-auf-tour/av-39101077",
        "http://www.dw.com/de/trump-sagt-nein-die-welt-schüttelt-den-kopf/av-39096724",
        "http://www.dw.com/el/ο-τραμπ-θεωρεί-την-ευρώπη-ανταγωνιστή-όχι-εταίρο/av-39103742",
        "http://www.dw.com/ar/أي-البروتينات-صحية-الحيوانية-أم-النباتية/av-39095317",
    ]
