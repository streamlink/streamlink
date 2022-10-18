from streamlink.plugins.tf1 import TF1
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlTF1(PluginCanHandleUrl):
    __plugin__ = TF1

    should_match_groups = [
        ("https://tf1.fr/tf1/direct", {"live": "tf1"}),
        ("https://www.tf1.fr/tf1/direct", {"live": "tf1"}),
        ("https://www.tf1.fr/tfx/direct", {"live": "tfx"}),
        ("https://www.tf1.fr/tf1-series-films/direct", {"live": "tf1-series-films"}),

        ("https://lci.fr/direct", {"lci": "lci"}),
        ("https://www.lci.fr/direct", {"lci": "lci"}),
        ("https://tf1info.fr/direct/", {"lci": "tf1info"}),
        ("https://www.tf1info.fr/direct/", {"lci": "tf1info"}),

        ("https://www.tf1.fr/stream/chante-69061019", {"stream": "chante-69061019"}),
        ("https://www.tf1.fr/stream/arsene-lupin-39652174", {"stream": "arsene-lupin-39652174"}),
    ]

    should_not_match = [
        "http://tf1.fr/direct",
        "http://www.tf1.fr/direct",
    ]
