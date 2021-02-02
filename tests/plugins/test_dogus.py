from streamlink.plugins.dogus import Dogus
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlDogus(PluginCanHandleUrl):
    __plugin__ = Dogus

    should_match = [
        'http://eurostartv.com.tr/canli-izle',
        'http://kralmuzik.com.tr/tv/',
        'http://ntv.com.tr/canli-yayin/ntv',
        'http://startv.com.tr/canli-yayin',
    ]

    should_not_match = [
        'http://www.ntvspor.net/canli-yayin',
    ]
