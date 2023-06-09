from streamlink.plugins.turkuvaz import Turkuvaz
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlTurkuvaz(PluginCanHandleUrl):
    __plugin__ = Turkuvaz

    should_match = [
        # canonical live links
        "https://www.ahaber.com.tr/video/canli-yayin",  # ahbr
        "https://www.ahaber.com.tr/canli-yayin-aspor.html",  # ahbr: aspor
        "https://www.ahaber.com.tr/canli-yayin-anews.html",  # ahbr: anews
        "https://www.ahaber.com.tr/canli-yayin-a2tv.html",  # ahbr: a2tv
        "https://www.ahaber.com.tr/canli-yayin-minikago.html",  # ahbr: minika go
        "https://www.ahaber.com.tr/canli-yayin-minikacocuk.html",  # ahbr: minika cocuk
        "https://www.anews.com.tr/webtv/live-broadcast",  # anews
        "https://www.apara.com.tr/canli-yayin",  # apara
        "https://www.aspor.com.tr/webtv/canli-yayin",  # aspor
        "https://www.atv.com.tr/canli-yayin",  # atv
        "https://www.atv.com.tr/a2tv/canli-yayin",  # a2tv
        "https://www.atvavrupa.tv/canli-yayin",  # atvavrupa
        "https://www.minikacocuk.com.tr/webtv/canli-yayin",  # minika cocuk
        "https://www.minikago.com.tr/webtv/canli-yayin",  # minika go
        "https://vavtv.com.tr/canli-yayin",  # vavtv

        # vods
        "https://www.ahaber.com.tr/video/yasam-videolari/samsunda-sel-sularindan-kacma-ani-kamerada",
        "https://www.anews.com.tr/webtv/world/pro-ukraine-militia-says-it-has-captured-russian-soldiers",
        "https://www.apara.com.tr/video/ekonomide-bugun/bist-100de-kar-satislari-derinlesir-mi",
        "https://www.aspor.com.tr/webtv/galatasaray/galatasaraydan-forma-tanitiminda-fenerbahceye-gonderme",
        "https://www.atv.com.tr/kurulus-osman/127-bolum/izle",
        "https://www.atvavrupa.tv/diger-program//ozelvideo/izle",
        "https://www.minikacocuk.com.tr/webtv/olly/bolum/olly-eylul-tanitim",
        "https://www.minikago.com.tr/webtv/mondo-yan/bolum/mondo-yan-eylul-tanitim",
        "https://vavtv.com.tr/vavradyo/video/guncel/munafiklarin-ozellikleri-nelerdir",

        # other links for info/doc
        "https://www.atv.com.tr/webtv/canli-yayin",  # redirect to atv.com.tr/canli-yayin
        "https://www.ahaber.com.tr/canli-yayin-atv.html",  # links to atv.com.tr/webtv/canli-yayin
    ]
