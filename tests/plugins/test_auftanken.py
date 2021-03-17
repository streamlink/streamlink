from streamlink.plugins.auftanken import AuftankenTV
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlAuftankenTV(PluginCanHandleUrl):
    __plugin__ = AuftankenTV

    should_match = [
        "https://www.auftanken.tv/livestream/",
        "https://auftanken.tv/livestream",
    ]
