from streamlink.plugins.vinhlongtv import VinhLongTV
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlVinhLongTV(PluginCanHandleUrl):
    __plugin__ = VinhLongTV

    should_match = [
        'http://thvli.vn/live/thvl1-hd/aab94d1f-44e1-4992-8633-6d46da08db42',
        'http://thvli.vn/live/thvl2-hd/bc60bddb-99ac-416e-be26-eb4d0852f5cc',
        'http://thvli.vn/live/phat-thanh/c87174ba-7aeb-4cb4-af95-d59de715464c',
    ]
