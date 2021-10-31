from streamlink.plugins.ltv_lsm_lv import LtvLsmLv
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlLtvLsmLv(PluginCanHandleUrl):
    __plugin__ = LtvLsmLv

    should_match = [
        "https://ltv.lsm.lv/lv/tiesraide/example/",
        "https://ltv.lsm.lv/lv/tiesraide/example/",
        "https://ltv.lsm.lv/lv/tiesraide/example/live.123/",
        "https://ltv.lsm.lv/lv/tiesraide/example/live.123/",
    ]

    should_not_match = [
        "https://ltv.lsm.lv",
        "http://ltv.lsm.lv",
        "https://ltv.lsm.lv/lv",
        "http://ltv.lsm.lv/lv",
        "https://ltv.lsm.lv/other-site/",
        "http://ltv.lsm.lv/other-site/",
        "https://ltv.lsm.lv/lv/other-site/",
        "http://ltv.lsm.lv/lv/other-site/",
        "https://ltv.lsm.lv/lv/tieshraide/example/",
    ]
