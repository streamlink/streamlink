from streamlink.plugins.telefe import Telefe
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlTelefe(PluginCanHandleUrl):
    __plugin__ = Telefe

    should_match = [
        "https://mitelefe.com/vivo",
        "https://mitelefe.com/vivo/",
    ]

    should_not_match = [
        "http://telefe.com/pone-a-francella/temporada-1/programa-01/",
        "http://telefe.com/los-simuladores/temporada-1/capitulo-01/",
        "http://telefe.com/dulce-amor/capitulos/capitulo-01/",
        "http://telefe.com/",
        "http://www.telefeinternacional.com.ar/",
        "http://marketing.telefe.com/",
    ]
