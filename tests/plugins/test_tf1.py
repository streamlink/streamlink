from streamlink.plugins.tf1 import TF1
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlTF1(PluginCanHandleUrl):
    __plugin__ = TF1

    should_match = [
        "http://tf1.fr/tf1/direct/",
        "http://tf1.fr/tfx/direct/",
        "http://tf1.fr/tf1-series-films/direct/",
        "http://lci.fr/direct",
        "http://www.lci.fr/direct",
        "http://tf1.fr/tmc/direct",
        "http://tf1.fr/lci/direct",
        "https://tf1info.fr/direct",
        "https://www.tf1.fr/stream/chante-69061019",
        "https://www.tf1.fr/stream/arsene-lupin-39652174"
    ]

    should_not_match = [
        "http://tf1.fr/direct",
        "http://www.tf1.fr/direct",
    ]
