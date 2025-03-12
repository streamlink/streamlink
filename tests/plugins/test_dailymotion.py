from streamlink.plugins.dailymotion import DailyMotion
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlDailyMotion(PluginCanHandleUrl):
    __plugin__ = DailyMotion

    should_match_groups = [
        (("user", "https://www.dailymotion.com/france24"), {"user": "france24"}),
        (("media", "https://www.dailymotion.com/video/x8dmdzz"), {"media_id": "x8dmdzz"}),
        (("media", "https://www.dailymotion.com/embed/video/x8dmdzz"), {"media_id": "x8dmdzz"}),
        (("lequipe", "https://www.lequipe.fr/tv/videos/live/k3HiS3JB0BsORKqwC49"), {}),
        (("lequipe", "https://www.lequipe.fr/tv/replay/le-resume-de-la-mass-start-du-grand-bornand/20201780"), {}),
    ]

    should_not_match = [
        "https://www.dailymotion.com/",
    ]
