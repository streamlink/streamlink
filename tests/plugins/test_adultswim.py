from streamlink.plugins.adultswim import AdultSwim
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlAdultSwim(PluginCanHandleUrl):
    __plugin__ = AdultSwim

    should_match = [
        "http://www.adultswim.com/streams",
        "http://www.adultswim.com/streams/",
        "https://www.adultswim.com/streams/infomercials",
        "https://www.adultswim.com/streams/last-stream-on-the-left-channel/",
        "https://www.adultswim.com/videos/as-seen-on-adult-swim/wednesday-march-18th-2020",
        "https://www.adultswim.com/videos/fishcenter-live/wednesday-april-29th-2020/"
    ]
