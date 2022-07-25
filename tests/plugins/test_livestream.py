from streamlink.plugins.livestream import Livestream
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlLivestream(PluginCanHandleUrl):
    __plugin__ = Livestream

    should_match_groups = [
        # no event/video
        (
            "https://livestream.com/accounts/12182108/",
            {"account": "12182108"},
        ),
        (
            "https://livestream.com/accounts/1538473/eaglecam",
            {"account": "1538473"},
        ),
        (
            "https://www.livestream.com/accounts/12182108/",
            {"subdomain": "www.", "account": "12182108"},
        ),
        # no event/video via API URL
        (
            "https://api.new.livestream.com/accounts/12182108/",
            {"subdomain": "api.new.", "account": "12182108"},
        ),
        # event
        (
            "https://livestream.com/accounts/12182108/events/4004765",
            {"account": "12182108", "event": "4004765"},
        ),
        (
            "https://www.livestream.com/accounts/12182108/events/4004765",
            {"subdomain": "www.", "account": "12182108", "event": "4004765"},
        ),
        # event via API URL
        (
            "https://api.new.livestream.com/accounts/12182108/events/4004765",
            {"subdomain": "api.new.", "account": "12182108", "event": "4004765"},
        ),
        # video without event
        (
            "https://livestream.com/accounts/4175709/neelix/videos/119637915",
            {"account": "4175709", "video": "119637915"},
        ),
        # video with event
        (
            "https://livestream.com/accounts/844142/events/5602516/videos/216545361",
            {"account": "844142", "event": "5602516", "video": "216545361"},
        ),
        # video with event via API URL
        (
            "https://api.new.livestream.com/accounts/844142/events/5602516/videos/216545361",
            {"subdomain": "api.new.", "account": "844142", "event": "5602516", "video": "216545361"},
        ),
    ]

    should_not_match = [
        "https://livestream.com/",
        "https://www.livestream.com/",
        "https://api.new.livestream.com/",
    ]
