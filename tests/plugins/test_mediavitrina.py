from streamlink.plugins.mediavitrina import MediaVitrina
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlMediaVitrina(PluginCanHandleUrl):
    __plugin__ = MediaVitrina

    should_match_groups = [
        (("chetv", "https://chetv.ru/online/"), {}),
        (("ctc", "https://ctc.ru/online/"), {}),
        (("ctc", "https://ctclove.ru/online/"), {}),
        (("domashniy", "https://domashniy.ru/online"), {}),
        (("mediavitrina", "https://player.mediavitrina.ru/5tv/moretv_web/player.html"), {}),
        (("mediavitrina", "https://player.mediavitrina.ru/che/che_web/player.html"), {}),
        (("mediavitrina", "https://player.mediavitrina.ru/ctc_ext/moretv_web/player.html"), {}),
        (("mediavitrina", "https://player.mediavitrina.ru/ctc_love_ext/moretv_web/player.html"), {}),
        (("mediavitrina", "https://player.mediavitrina.ru/ctc_love/ctclove_web/player.html"), {}),
        (("mediavitrina", "https://player.mediavitrina.ru/ctc/ctcmedia_web/player.html?start=auto"), {}),
        (("mediavitrina", "https://player.mediavitrina.ru/domashniy_ext/moretv_web/player.html"), {}),
        (("mediavitrina", "https://player.mediavitrina.ru/domashniy/dom_web/player.html?start=auto"), {}),
        (("mediavitrina", "https://player.mediavitrina.ru/gpm_tv3_v2/tv3/smotrim_web/611632488a33a/player.html"), {}),
        (("mediavitrina", "https://player.mediavitrina.ru/iz/moretv_web/player.html"), {}),
        (("mediavitrina", "https://player.mediavitrina.ru/kultura/limehd_web/player.html"), {}),
        (("mediavitrina", "https://player.mediavitrina.ru/kultura/moretv_web/player.html"), {}),
        (("mediavitrina", "https://player.mediavitrina.ru/mir/mir/moretv_web/player.html"), {}),
        (("mediavitrina", "https://player.mediavitrina.ru/muztv/moretv_web/player.html"), {}),
        (("mediavitrina", "https://player.mediavitrina.ru/rentv/moretv_web/player.html"), {}),
        (("mediavitrina", "https://player.mediavitrina.ru/russia1/mailru_web/player.html"), {}),
        (("mediavitrina", "https://player.mediavitrina.ru/russia1/moretv_web/player.html"), {}),
        (("mediavitrina", "https://player.mediavitrina.ru/russia24/moretv_web/player.html"), {}),
        (("mediavitrina", "https://player.mediavitrina.ru/russia24/vesti_ru_web/player.html?id"), {}),
        (("mediavitrina", "https://player.mediavitrina.ru/spas/moretv_web/player.html"), {}),
        (("mediavitrina", "https://player.mediavitrina.ru/tvc/tvc/moretv_web/player.html"), {}),
        (("mediavitrina", "https://player.mediavitrina.ru/tvzvezda/moretv_web/player.html"), {}),
        (("mediavitrina", "https://player.mediavitrina.ru/u_ott/u/moretv_web/player.html"), {}),
        (("mediavitrina", "https://player.mediavitrina.ru/gpm_tnt_v2/tnt/vitrinatv_web/player.html"), {}),
    ]

    should_not_match = [
        "https://1tv.ru/live",
        "https://ren.tv/live",
        "https://www.5-tv.ru/live/",
        "https://www.5-tv.ru/online/",
    ]
