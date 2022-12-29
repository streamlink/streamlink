from streamlink.plugins.vkplay import VKplay
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlVKplay(PluginCanHandleUrl):
    __plugin__ = VKplay

    should_match = [
        "https://vkplay.live/Channel_Name_123",
    ]

    should_not_match = [
        "https://vkplay.live/",
        "https://support.vkplay.ru/vkp_live",
        "https://vkplay.live/app/settings/edit",
        "https://vkplay.live/app/settings/external-apps",
    ]
