import pytest

from streamlink.plugins.goodgame import GoodGame
from streamlink.session import Streamlink
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlGoodGame(PluginCanHandleUrl):
    __plugin__ = GoodGame

    should_match_groups = [
        ("https://goodgame.ru/CHANNELNAME", {"user": "CHANNELNAME"}),
        ("https://goodgame.ru/channel/CHANNELNAME", {"user": "CHANNELNAME"}),
    ]


@pytest.mark.parametrize(("url", "expected"), [
    ("https://goodgame.ru/CHANNELNAME", "https://goodgame.ru/CHANNELNAME"),
    ("https://goodgame.ru/channel/CHANNELNAME", "https://goodgame.ru/CHANNELNAME"),
])
def test_url_translation(session: Streamlink, url: str, expected: str):
    plugin = GoodGame(session, url)
    assert plugin.url == expected
