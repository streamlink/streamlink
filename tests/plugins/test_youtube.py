from unittest.mock import Mock

import pytest

from streamlink.plugins.youtube import YouTube
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlYouTube(PluginCanHandleUrl):
    __plugin__ = YouTube

    should_match_groups = [
        (("default", "https://www.youtube.com/v/aqz-KE-bpKQ"), {
            "video_id": "aqz-KE-bpKQ",
        }),
        (("default", "https://www.youtube.com/live/aqz-KE-bpKQ"), {
            "video_id": "aqz-KE-bpKQ",
        }),
        (("default", "https://www.youtube.com/watch?foo=bar&baz=qux&v=aqz-KE-bpKQ&asdf=1234"), {
            "video_id": "aqz-KE-bpKQ",
        }),

        (("channel", "https://www.youtube.com/CHANNELNAME"), {
            "channel": "CHANNELNAME",
        }),
        (("channel", "https://www.youtube.com/CHANNELNAME/live"), {
            "channel": "CHANNELNAME",
            "live": "/live",
        }),
        (("channel", "https://www.youtube.com/@CHANNELNAME"), {
            "channel": "CHANNELNAME",
        }),
        (("channel", "https://www.youtube.com/@CHANNELNAME/live"), {
            "channel": "CHANNELNAME",
            "live": "/live",
        }),
        (("channel", "https://www.youtube.com/c/CHANNELNAME"), {
            "channel": "CHANNELNAME",
        }),
        (("channel", "https://www.youtube.com/c/CHANNELNAME/live"), {
            "channel": "CHANNELNAME",
            "live": "/live",
        }),
        (("channel", "https://www.youtube.com/channel/CHANNELID"), {
            "channel": "CHANNELID",
        }),
        (("channel", "https://www.youtube.com/channel/CHANNELID/live"), {
            "channel": "CHANNELID",
            "live": "/live",
        }),
        (("channel", "https://www.youtube.com/user/CHANNELNAME"), {
            "channel": "CHANNELNAME",
        }),
        (("channel", "https://www.youtube.com/user/CHANNELNAME/live"), {
            "channel": "CHANNELNAME",
            "live": "/live",
        }),

        (("embed", "https://www.youtube.com/embed/aqz-KE-bpKQ"), {
            "video_id": "aqz-KE-bpKQ",
        }),
        (("embed", "https://www.youtube.com/embed/live_stream?channel=CHANNELNAME"), {
            "live": "CHANNELNAME",
        }),

        (("shorthand", "https://youtu.be/aqz-KE-bpKQ"), {
            "video_id": "aqz-KE-bpKQ",
        }),
    ]

    should_not_match = [
        "https://accounts.google.com/",
        "https://www.youtube.com",
        "https://www.youtube.com/",
        "https://www.youtube.com/feed/guide_builder",
        "https://www.youtube.com/t/terms",
        "https://youtu.be",
        "https://youtu.be/",
        "https://youtu.be/c/CHANNELNAME",
        "https://youtu.be/c/CHANNELNAME/live",
    ]


@pytest.mark.parametrize(("url", "expected"), [
    ("http://gaming.youtube.com/watch?v=0123456789A", "https://www.youtube.com/watch?v=0123456789A"),
    ("http://youtu.be/0123456789A", "https://www.youtube.com/watch?v=0123456789A"),
    ("http://youtube.com/embed/0123456789A", "https://www.youtube.com/watch?v=0123456789A"),
    ("http://youtube.com/embed/live_stream?channel=CHANNELID", "https://www.youtube.com/channel/CHANNELID/live"),
    ("http://www.youtube.com/watch?v=0123456789A", "https://www.youtube.com/watch?v=0123456789A"),
])
def test_translate_url(url, expected):
    assert YouTube(Mock(), url).url == expected
