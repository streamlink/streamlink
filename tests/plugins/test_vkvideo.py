from streamlink.plugins.vkvideo import VKvideo
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlVKvideo(PluginCanHandleUrl):
    __plugin__ = VKvideo

    should_match = [
        "https://live.vkvideo.ru/CHANNEL",
        "https://live.vkplay.ru/CHANNEL",
        "https://vkplay.live/CHANNEL",
    ]

    should_not_match = [
        "https://live.vkvideo.ru/",
        "https://live.vkplay.ru/",
        "https://vkplay.live/",
        "https://support.vkplay.ru/vkp_live",
        "https://vkplay.live/app/settings/edit",
        "https://vkplay.live/app/settings/external-apps",
    ]
