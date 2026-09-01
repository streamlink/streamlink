from streamlink.plugins.vimeo import Vimeo
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlVimeo(PluginCanHandleUrl):
    __plugin__ = Vimeo

    should_match_groups = [
        (("default", "https://vimeo.com/783455878"), {"video_id": "783455878"}),
        (("default", "https://vimeo.com/channels/music/176894130"), {"video_id": "176894130"}),
        (("default", "https://vimeo.com/ondemand/worldoftomorrow3/467204924"), {"video_id": "467204924"}),
        (("default", "https://player.vimeo.com/video/176894130"), {"video_id": "176894130"}),
        (("event", "https://vimeo.com/event/6149301"), {"event_id": "6149301"}),
        (("event", "https://vimeo.com/event/6149301/embed"), {"event_id": "6149301"}),
    ]

    should_not_match = [
        "https://www.vimeo.com/",
    ]
