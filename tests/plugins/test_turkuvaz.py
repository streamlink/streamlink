from streamlink.plugins.turkuvaz import Turkuvaz
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlTurkuvaz(PluginCanHandleUrl):
    __plugin__ = Turkuvaz

    should_match = [
        'http://www.atv.com.tr/a2tv/canli-yayin',
        'https://www.atv.com.tr/a2tv/canli-yayin',
        'https://www.atv.com.tr/webtv/canli-yayin',
        'http://www.a2tv.com.tr/webtv/canli-yayin',
        'http://www.ahaber.com.tr/video/canli-yayin',
        'https://www.ahaber.com.tr/video/canli-yayin',
        'https://www.ahaber.com.tr/webtv/canli-yayin',
        'https://www.aspor.com.tr/webtv/canli-yayin',
        'http://www.anews.com.tr/webtv/live-broadcast',
        'http://www.atvavrupa.tv/webtv/canli-yayin',
        'http://www.minikacocuk.com.tr/webtv/canli-yayin',
        'http://www.minikago.com.tr/webtv/canli-yayin',
        'https://www.sabah.com.tr/apara/canli-yayin',
    ]
