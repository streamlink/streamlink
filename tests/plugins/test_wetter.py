from streamlink.plugins.wetter import Wetter
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlWetter(PluginCanHandleUrl):
    __plugin__ = Wetter

    should_match = [
        "https://wetter.com/hd-live-webcams/kroatien/panorama-split-webcam-riva/5c81ccdea5b4b9130764ead8/",
        "http://www.wetter.com/hd-live-webcams/deutschland/hamburg-elbe/5152d06034178/",
    ]
