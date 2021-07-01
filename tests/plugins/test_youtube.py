import pytest

from streamlink.plugin import Plugin
from streamlink.plugins.youtube import YouTube
from tests.mock import Mock
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlYouTube(PluginCanHandleUrl):
    __plugin__ = YouTube

    should_match = [
        "https://www.youtube.com/EXAMPLE/live",
        "https://www.youtube.com/EXAMPLE/live/",
        "https://www.youtube.com/c/EXAMPLE/live",
        "https://www.youtube.com/c/EXAMPLE/live/",
        "https://www.youtube.com/channel/EXAMPLE/live",
        "https://www.youtube.com/channel/EXAMPLE/live/",
        "https://www.youtube.com/user/EXAMPLE/live",
        "https://www.youtube.com/user/EXAMPLE/live/",
        "https://www.youtube.com/embed/aqz-KE-bpKQ",
        "https://www.youtube.com/embed/live_stream?channel=UCNye-wNBqNL5ZzHSJj3l8Bg",
        "https://www.youtube.com/v/aqz-KE-bpKQ",
        "https://www.youtube.com/watch?v=aqz-KE-bpKQ",
        "https://www.youtube.com/watch?foo=bar&baz=qux&v=aqz-KE-bpKQ",
        "https://youtu.be/0123456789A",
    ]

    should_not_match = [
        "https://accounts.google.com/",
        "https://www.youtube.com",
        "https://www.youtube.com/account",
        "https://www.youtube.com/feed/guide_builder",
        "https://www.youtube.com/t/terms",
        "https://www.youtube.com/c/EXAMPLE",
        "https://www.youtube.com/channel/EXAMPLE",
        "https://www.youtube.com/user/EXAMPLE",
        "https://youtu.be",
        "https://youtu.be/",
        "https://youtu.be/c/CHANNEL",
        "https://youtu.be/c/CHANNEL/live",
    ]


@pytest.mark.parametrize("url,group,expected", [
    ("https://www.youtube.com/v/aqz-KE-bpKQ", "video_id", "aqz-KE-bpKQ"),
    ("https://www.youtube.com/embed/aqz-KE-bpKQ", "video_id", "aqz-KE-bpKQ"),
    ("https://www.youtube.com/watch?v=aqz-KE-bpKQ", "video_id", "aqz-KE-bpKQ"),
])
def test_match_url(url, group, expected):
    Plugin.bind(Mock(), "tests.plugins.test_youtube")
    plugin = YouTube(url)
    assert plugin.match is not None
    assert plugin.match.group(group) == expected


@pytest.mark.parametrize("url,expected", [
    ("http://gaming.youtube.com/watch?v=0123456789A", "https://www.youtube.com/watch?v=0123456789A"),
    ("http://youtu.be/0123456789A", "https://www.youtube.com/watch?v=0123456789A"),
    ("http://youtube.com/embed/0123456789A", "https://www.youtube.com/watch?v=0123456789A"),
    ("http://youtube.com/embed/live_stream?channel=CHANNELID", "https://www.youtube.com/channel/CHANNELID/live"),
    ("http://www.youtube.com/watch?v=0123456789A", "https://www.youtube.com/watch?v=0123456789A"),
])
def test_translate_url(url, expected):
    Plugin.bind(Mock(), "tests.plugins.test_youtube")
    assert YouTube(url).url == expected
