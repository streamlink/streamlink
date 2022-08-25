from unittest.mock import Mock

import pytest

from streamlink.plugins.youtube import YouTube
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlYouTube(PluginCanHandleUrl):
    __plugin__ = YouTube

    should_match = [
        "https://www.youtube.com/CHANNELNAME",
        "https://www.youtube.com/CHANNELNAME/",
        "https://www.youtube.com/CHANNELNAME/live",
        "https://www.youtube.com/CHANNELNAME/live/",
        "https://www.youtube.com/c/CHANNELNAME",
        "https://www.youtube.com/c/CHANNELNAME/",
        "https://www.youtube.com/c/CHANNELNAME/live",
        "https://www.youtube.com/c/CHANNELNAME/live/",
        "https://www.youtube.com/user/CHANNELNAME",
        "https://www.youtube.com/user/CHANNELNAME/",
        "https://www.youtube.com/user/CHANNELNAME/live",
        "https://www.youtube.com/user/CHANNELNAME/live/",
        "https://www.youtube.com/channel/CHANNELID",
        "https://www.youtube.com/channel/CHANNELID/",
        "https://www.youtube.com/channel/CHANNELID/live",
        "https://www.youtube.com/channel/CHANNELID/live/",
        "https://www.youtube.com/embed/aqz-KE-bpKQ",
        "https://www.youtube.com/embed/live_stream?channel=UCNye-wNBqNL5ZzHSJj3l8Bg",
        "https://www.youtube.com/v/aqz-KE-bpKQ",
        "https://www.youtube.com/watch?v=aqz-KE-bpKQ",
        "https://www.youtube.com/watch?foo=bar&baz=qux&v=aqz-KE-bpKQ",
        "https://youtu.be/0123456789A",
    ]

    should_match_groups = [
        ("https://www.youtube.com/v/aqz-KE-bpKQ", {
            "video_id": "aqz-KE-bpKQ",
        }),
        ("https://www.youtube.com/embed/aqz-KE-bpKQ", {
            "embed": "embed",
            "video_id": "aqz-KE-bpKQ",
        }),
        ("https://www.youtube.com/watch?v=aqz-KE-bpKQ", {
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


@pytest.mark.parametrize("url,expected", [
    ("http://gaming.youtube.com/watch?v=0123456789A", "https://www.youtube.com/watch?v=0123456789A"),
    ("http://youtu.be/0123456789A", "https://www.youtube.com/watch?v=0123456789A"),
    ("http://youtube.com/embed/0123456789A", "https://www.youtube.com/watch?v=0123456789A"),
    ("http://youtube.com/embed/live_stream?channel=CHANNELID", "https://www.youtube.com/channel/CHANNELID/live"),
    ("http://www.youtube.com/watch?v=0123456789A", "https://www.youtube.com/watch?v=0123456789A"),
])
def test_translate_url(url, expected):
    assert YouTube(Mock(), url).url == expected
