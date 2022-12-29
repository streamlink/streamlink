from streamlink.plugins.vkplay import VKplay
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlAbemaTV(PluginCanHandleUrl):
    __plugin__ = VKplay

    should_match = [
        'https://vkplay.live/dsadasllda',
        'https://vkplay.live/dsadas231',
        'https://vkplay.live/p4ds_flob3k',
        'https://vkplay.live/901237691',
    ]

    should_not_match = [
        'https://vkplay.live/',
        'https://support.vkplay.ru/vkp_live',
        'https://vkplay.live/app/settings/edit',
        'https://vkplay.live/app/settings/external-apps'
    ]
