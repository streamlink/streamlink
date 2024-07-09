from streamlink.plugins.rumble import Rumble
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlRumble(PluginCanHandleUrl):
    __plugin__ = Rumble

    should_match_groups = [
        (("channel", "https://rumble.com/c/CHANNEL"), {"channel": "CHANNEL"}),
        (("channel", "https://rumble.com/c/CHANNEL/livestreams"), {"channel": "CHANNEL"}),
        (("live", "https://rumble.com/ROOM_ID.html"), {"room_id": "ROOM_ID"}),
    ]

    should_not_match = [
        "https://rumble.com",
    ]
