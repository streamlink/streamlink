from streamlink.plugins.turkuvaz import Turkuvaz
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlTurkuvaz(PluginCanHandleUrl):
    __plugin__ = Turkuvaz

    should_match = [
        "https://www.ahaber.com.tr/video/canli-yayin",
        "https://www.ahaber.com.tr/webtv/canli-yayin",
        "https://www.anews.com.tr/webtv/live-broadcast",
        "https://www.apara.com.tr/canli-yayin",
        "https://www.aspor.com.tr/webtv/canli-yayin",
        "https://www.atv.com.tr/a2tv/canli-yayin",
        "https://www.atv.com.tr/webtv/canli-yayin",
        "https://www.atvavrupa.tv/webtv/canli-yayin",
        "https://www.minikacocuk.com.tr/webtv/canli-yayin",
        "https://www.minikago.com.tr/webtv/canli-yayin",
        "https://www.vavtv.com.tr/canli-yayin",
    ]
