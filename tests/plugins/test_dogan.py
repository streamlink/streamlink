from streamlink.plugins.dogan import Dogan
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlDogan(PluginCanHandleUrl):
    __plugin__ = Dogan

    should_match = [
        "https://www.cnnturk.com/canli-yayin",
        "https://www.cnnturk.com/action/embedvideo/5fa56d065cf3b018a8dd0bbc",
        "https://www.cnnturk.com/tv-cnn-turk/belgeseller/bir-zamanlar/bir-zamanlar-90lar-belgeseli",
        "https://www.cnnturk.com/video/turkiye/polis-otomobiliyle-tur-atan-sahisla-ilgili-islem-baslatildi-video",

        "https://www.dreamturk.com.tr/canli-yayin-izle",
        "https://www.dreamturk.com.tr/dream-turk-ozel/radyo-d/ilyas-yalcintas-radyo-dnin-konugu-oldu",
        "https://www.dreamturk.com.tr/programlar/dream-10",
        "https://www.dreamtv.com.tr/dream-ozel/konserler/acik-sahne-dream-ozel",

        "https://www.teve2.com.tr/canli-yayin",
        "https://www.teve2.com.tr/diziler/guncel/oyle-bir-gecer-zaman-ki/bolumler/oyle-bir-gecer-zaman-ki-1-bolum",
        "https://www.teve2.com.tr/embed/55f6d5b8402011f264ec7f64",
        "https://www.teve2.com.tr/filmler/guncel/yasamak-guzel-sey",
        "https://www.teve2.com.tr/programlar/guncel/kelime-oyunu/bolumler/kelime-oyunu-800-bolum-19-12-2020",

        "https://www.kanald.com.tr/canli-yayin",
        "https://www.kanald.com.tr/embed/5fda41a8ebc8302048167df6",
        "https://www.kanald.com.tr/sadakatsiz/fragmanlar/sadakatsiz-10-bolum-fragmani",
    ]
