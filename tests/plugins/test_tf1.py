from streamlink.plugins.tf1 import TF1
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlTF1(PluginCanHandleUrl):
    __plugin__ = TF1

    should_match_groups = [
        (("live", "https://tf1.fr/tf1/direct"), {"live": "tf1"}),
        (("live", "https://www.tf1.fr/tf1/direct"), {"live": "tf1"}),
        (("live", "https://www.tf1.fr/tfx/direct"), {"live": "tfx"}),
        (("live", "https://www.tf1.fr/tf1-series-films/direct"), {"live": "tf1-series-films"}),
        (("stream", "https://www.tf1.fr/chante-69061019/direct"), {"stream": "chante-69061019"}),
        (("stream", "https://www.tf1.fr/thriller-fiction-89242722/direct"), {"stream": "thriller-fiction-89242722"}),
        (("lci", "https://lci.fr/direct"), {}),
        (("lci", "https://www.lci.fr/direct"), {}),
        (("lci", "https://tf1info.fr/direct/"), {}),
        (("lci", "https://www.tf1info.fr/direct/"), {}),
    ]

    should_not_match = [
        "http://tf1.fr/direct",
        "http://www.tf1.fr/direct",
    ]
