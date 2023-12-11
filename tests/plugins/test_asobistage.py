from streamlink.plugins.asobistage import AsobiStage
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlAsobiStage(PluginCanHandleUrl):
    __plugin__ = AsobiStage

    should_match_groups = [
        (
            "https://asobistage.asobistore.jp/event/ijigenfes_utagassen/player/day1",
            {"id": "ijigenfes_utagassen/player/day1", "type": "player"},
        ),
        (
            "https://asobistage.asobistore.jp/event/ijigenfes_utagassen/archive/day2",
            {"id": "ijigenfes_utagassen/archive/day2", "type": "archive"},
        ),
        (
            "https://asobistage.asobistore.jp/event/sidem_fclive_bpct/archive/premium_hc",
            {"id": "sidem_fclive_bpct/archive/premium_hc", "type": "archive"},
        ),
        (
            "https://asobistage.asobistore.jp/event/idolmaster_idolworld2023_goods/archive/live",
            {"id": "idolmaster_idolworld2023_goods/archive/live", "type": "archive"},
        ),
    ]

    should_not_match = [
        # homepage
        "https://asobistage.asobistore.jp/",
        # other pages
        "https://asobistage.asobistore.jp/event/ijigenfes_utagassen/entrance",
        "https://asobistage.asobistore.jp/event/denonbu_denonbu_2nd/rental/ticket",
        # rental tickets
        "https://asobistage.asobistore.jp/event/denonbu_areameeting_harajuku/rental/player/kinobu",
        "https://asobistage.asobistore.jp/event/denonbu_denonbu_2nd/rental/player/kannazuki",
    ]
