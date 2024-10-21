from streamlink.plugins.vimeo import Vimeo
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlVimeo(PluginCanHandleUrl):
    __plugin__ = Vimeo

    should_match_groups = [
        (("default", "https://vimeo.com/783455878"), {}),
        (("default", "https://vimeo.com/channels/music/176894130"), {}),
        (("default", "https://vimeo.com/ondemand/worldoftomorrow3/467204924"), {}),
        (("default", "https://vimeo.com/ondemand/100footsurfingdays"), {}),
        (("player", "https://player.vimeo.com/video/176894130"), {}),
        (("event", "https://vimeo.com/event/4154130"), {"event_id": "4154130"}),
        (("event", "https://vimeo.com/event/4154130/embed"), {"event_id": "4154130"}),
    ]

    should_not_match = [
        "https://www.vimeo.com/",
    ]
