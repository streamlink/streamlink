from streamlink.plugins.dailymotion import DailyMotion
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlDailyMotion(PluginCanHandleUrl):
    __plugin__ = DailyMotion

    should_match = [
        "https://www.dailymotion.com/video/xigbvx",
        "https://www.dailymotion.com/france24",
        "https://www.dailymotion.com/embed/video/xigbvx",
    ]

    should_not_match = [
        "https://www.dailymotion.com/",
    ]
