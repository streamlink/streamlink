from streamlink.plugins.galatasaraytv import GalatasarayTV
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlGalatasarayTV(PluginCanHandleUrl):
    __plugin__ = GalatasarayTV

    should_match = [
        'http://galatasaray.com/',
        'https://galatasaray.com',
        'https://galatasaray.com/',
        'https://www.galatasaray.com/',
    ]
