from streamlink.plugins.dogan import Dogan
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlDogan(PluginCanHandleUrl):
    __plugin__ = Dogan

    should_match = [
        ("cnnturk", "https://www.cnnturk.com/canli-yayin"),
        ("cnnturk", "https://www.cnnturk.com/action/embedvideo/5fa56d065cf3b018a8dd0bbc"),
        ("cnnturk", "https://www.cnnturk.com/tv-cnn-turk/belgeseller/bir-zamanlar/bir-zamanlar-90lar-belgeseli"),
        ("cnnturk", "https://www.cnnturk.com/video/turkiye/polis-savci-yalaniyla-750-bin-tl-vurgun-3471550"),
        ("dreamturk", "https://www.dreamturk.com.tr/canli-yayin-izle"),
        ("dreamturk", "https://www.dreamtv.com.tr/dream-ozel/konserler/acik-sahne-dream-ozel"),
        ("kanald", "https://www.kanald.com.tr/canli-yayin"),
        ("kanald", "https://www.kanald.com.tr/embed/6ab244408e6adc7618129ec4"),
        ("kanald", "https://www.kanald.com.tr/haysiyet/bolumler/haysiyet-son-bolum"),
    ]
