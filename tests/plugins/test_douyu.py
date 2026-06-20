from streamlink.plugins.douyu import Douyu
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlDouyu(PluginCanHandleUrl):
    __plugin__ = Douyu

    should_match = [
        "https://www.douyu.com/12345",
        "https://www.douyu.com/topic/12345",
        "http://www.douyu.com/999",
    ]

    should_match_groups = [
        ("https://www.douyu.com/288016", {"rid": "288016"}),
        ("https://www.douyu.com/topic/12345", {"rid": "12345"}),
    ]

    should_not_match = [
        "https://www.douyu.com/",
        "https://www.douyu.com/member/cp",
        "https://www.douyu.com/abc_def",
    ]
