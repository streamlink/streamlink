from streamlink.plugins.zattoo import Zattoo
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlZattoo(PluginCanHandleUrl):
    __plugin__ = Zattoo

    should_match = [
        # mirrors
        "https://iptv.glattvision.ch/watch/ard",
        "https://mobiltv.quickline.com/watch/ard",
        "https://player.waly.tv/watch/ard",
        "https://tvplus.m-net.de/watch/ard",
        "https://www.bbv-tv.net/watch/ard",
        "https://www.meinewelt.cc/watch/ard",
        "https://www.netplus.tv/watch/ard",
        "https://www.quantum-tv.com/watch/ard",
        "https://www.saktv.ch/watch/ard",
        "https://www.vtxtv.ch/watch/ard",
        "http://tvonline.ewe.de/watch/daserste",
        "http://tvonline.ewe.de/watch/zdf",
        "https://nettv.netcologne.de/watch/daserste",
        "https://nettv.netcologne.de/watch/zdf",
        "https://www.1und1.tv/watch/daserste",
        "https://www.1und1.tv/watch/zdf",
        # zattoo live
        "https://zattoo.com/watch/daserste",
        "https://zattoo.com/watch/zdf",
        "https://zattoo.com/live/zdf",
        "https://zattoo.com/channels?channel=daserste",
        "https://zattoo.com/channels/favorites?channel=zdf",
        "https://zattoo.com/channels/zattoo?channel=zdf",
        # zattoo vod
        "https://zattoo.com/ondemand/watch/ibR2fpisWFZGvmPBRaKnFnuT-alarm-am-airport",
        "https://zattoo.com/ondemand/watch/G8S7JxcewY2jEwAgMzvFWK8c-berliner-schnauzen",
        "https://zattoo.com/ondemand?video=x4hUTiCv4FLAA72qLvahiSFp",
        # zattoo recording
        "https://zattoo.com/ondemand/watch/srf_zwei/110223896-die-schweizermacher/52845783/1455130800000"
        + "/1455137700000/6900000",
        "https://zattoo.com/watch/tve/130920738-viaje-al-centro-de-la-tele/96847859/1508777100000/1508779800000/0",
        "https://zattoo.com/recording/193074536",
        "https://zattoo.com/recordings?recording=186466965",
    ]

    should_not_match = [
        "https://ewe.de",
        "https://netcologne.de",
        "https://zattoo.com",
    ]
