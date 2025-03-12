from streamlink.plugins.turkuvaz import Turkuvaz
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlTurkuvaz(PluginCanHandleUrl):
    __plugin__ = Turkuvaz

    should_match_groups = [
        # canonical live links
        (("ahaber", "https://www.ahaber.com.tr/video/canli-yayin"), {}),  # ahbr
        (("ahaber", "https://www.ahaber.com.tr/canli-yayin-aspor.html"), {}),  # ahbr: aspor
        (("ahaber", "https://www.ahaber.com.tr/canli-yayin-anews.html"), {}),  # ahbr: anews
        (("ahaber", "https://www.ahaber.com.tr/canli-yayin-a2tv.html"), {}),  # ahbr: a2tv
        (("ahaber", "https://www.ahaber.com.tr/canli-yayin-minikago.html"), {}),  # ahbr: minika go
        (("ahaber", "https://www.ahaber.com.tr/canli-yayin-minikacocuk.html"), {}),  # ahbr: minika cocuk
        (("anews", "https://www.anews.com.tr/webtv/live-broadcast"), {}),  # anews
        (("apara", "https://www.apara.com.tr/canli-yayin"), {}),  # apara
        (("aspor", "https://www.aspor.com.tr/webtv/canli-yayin"), {}),  # aspor
        (("atv", "https://www.atv.com.tr/canli-yayin"), {}),  # atv
        (("atv", "https://www.atv.com.tr/a2tv/canli-yayin"), {}),  # a2tv
        (("atvavrupa", "https://www.atvavrupa.tv/canli-yayin"), {}),  # atvavrupa
        (("minikacocuk", "https://www.minikacocuk.com.tr/webtv/canli-yayin"), {}),  # minika cocuk
        (("minikago", "https://www.minikago.com.tr/webtv/canli-yayin"), {}),  # minika go
        (("vavtv", "https://vavtv.com.tr/canli-yayin"), {}),  # vavtv
        # vods
        (("ahaber", "https://www.ahaber.com.tr/video/yasam-videolari/samsunda-sel-sularindan-kacma-ani-kamerada"), {}),
        (("anews", "https://www.anews.com.tr/webtv/world/pro-ukraine-militia-says-it-has-captured-russian-soldiers"), {}),
        (("apara", "https://www.apara.com.tr/video/ekonomide-bugun/bist-100de-kar-satislari-derinlesir-mi"), {}),
        (("aspor", "https://www.aspor.com.tr/webtv/galatasaray/galatasaraydan-forma-tanitiminda-fenerbahceye-gonderme"), {}),
        (("atvavrupa", "https://www.atvavrupa.tv/diger-program//ozelvideo/izle"), {}),
        (("minikago", "https://www.minikago.com.tr/webtv/mondo-yan/bolum/mondo-yan-eylul-tanitim"), {}),
        (("vavtv", "https://vavtv.com.tr/vavradyo/video/guncel/munafiklarin-ozellikleri-nelerdir"), {}),
        # other links for info/doc
        (("atv", "https://www.atv.com.tr/webtv/canli-yayin"), {}),  # redirect to atv.com.tr/canli-yayin
        (("ahaber", "https://www.ahaber.com.tr/canli-yayin-atv.html"), {}),  # links to atv.com.tr/webtv/canli-yayin
    ]
