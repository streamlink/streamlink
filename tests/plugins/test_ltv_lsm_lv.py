from streamlink.plugins.ltv_lsm_lv import LtvLsmLv
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlLtvLsmLv(PluginCanHandleUrl):
    __plugin__ = LtvLsmLv

    should_match = [
        "https://ltv.lsm.lv/lv/tiesraide/ltv1",
        "https://ltv.lsm.lv/lv/tiesraide/ltv7",
        "https://ltv.lsm.lv/lv/tiesraide/visiem",
        "https://ltv.lsm.lv/lv/tiesraide/lr1",
        "https://ltv.lsm.lv/lv/tiesraide/lr2",
        "https://ltv.lsm.lv/lv/tiesraide/lr3",
        "https://ltv.lsm.lv/lv/tiesraide/lr4",
        "https://ltv.lsm.lv/lv/tiesraide/lr5",
        "https://ltv.lsm.lv/lv/tiesraide/lr6",
        "https://replay.lsm.lv/lv/tiesraide/ltv7/sporta-studija-aizkulises",
        "https://replay.lsm.lv/ru/efir/ltv7/sporta-studija-aizkulises",
    ]
