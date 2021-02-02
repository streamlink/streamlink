from streamlink.plugins.mrtmk import MRTmk
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlMRTmk(PluginCanHandleUrl):
    __plugin__ = MRTmk

    should_match = [
        'http://play.mrt.com.mk/live/658323455489957',
        'http://play.mrt.com.mk/live/47',
        'http://play.mrt.com.mk/play/1581',
    ]

    should_not_match = [
        'http://play.mrt.com.mk/',
        'http://play.mrt.com.mk/c/2',
    ]
