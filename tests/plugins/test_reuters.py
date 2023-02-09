from streamlink.plugins.reuters import Reuters
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlReuters(PluginCanHandleUrl):
    __plugin__ = Reuters

    should_match = [
        "https://uk.reuters.com/video/watch/east-africa-battles-locust-invasion-idOVC2J9BHJ?chan=92jv7sln",
        "https://www.reuters.com/livevideo?id=Pdeb",
        "https://www.reuters.com/video/watch/baby-yoda-toy-makes-its-big-debut-idOVC1KAO9Z?chan=8adtq7aq",
        "https://www.reuters.tv/l/PFJx/2019/04/19/way-of-the-cross-ritual-around-notre-dame-cathedral",
        "https://www.reuters.tv/l/PFcO/2019/04/10/first-ever-black-hole-image-released-astrophysics-milestone",
        "https://www.reuters.tv/p/WoRwM1a00y8",
    ]
