from streamlink.plugins.vkvideolive import VKvideolive
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlVKvideolive(PluginCanHandleUrl):
    __plugin__ = VKvideolive

    should_match = [
        # live
        "https://live.vkvideo.ru/CHANNEL",
        "https://live.vkplay.ru/CHANNEL",
        "https://vkplay.live/CHANNEL",
        # VOD
        "https://live.vkvideo.ru/CHANNEL/record/VOD",
        "https://live.vkplay.ru/CHANNEL/record/VOD",
        "https://vkplay.live/CHANNEL/record/VOD",
    ]

    should_not_match = [
        "https://live.vkvideo.ru/",
        "https://live.vkplay.ru/",
        "https://vkplay.live/",
        "https://support.vkplay.ru/vkp_live",
        "https://vkplay.live/app/settings/edit",
        "https://vkplay.live/app/settings/external-apps",
    ]
