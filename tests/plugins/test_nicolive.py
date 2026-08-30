import argparse

import pytest

from streamlink.plugins.nicolive import NicoLive
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlNicoLive(PluginCanHandleUrl):
    __plugin__ = NicoLive

    should_match = [
        "https://live.nicovideo.jp/watch/lv123",
        "https://live2.nicovideo.jp/watch/lv123",
        "https://live2.nicovideo.jp/watch/lv123?ref=rtrec&zroute=recent",
        "https://live.nicovideo.jp/watch/co456?ref=community",
        "https://live.nicovideo.jp/watch/co456",
        "https://live.nicovideo.jp/watch/user/789",
    ]


class TestNicoLiveArguments:
    @pytest.fixture()
    def parser(self):
        parser = argparse.ArgumentParser()
        for parg in NicoLive.arguments or []:
            parser.add_argument(parg.argument_name("nicolive"), **parg.options)

        return parser

    @pytest.mark.parametrize("timeshift_offset", ["123", "123.45"])
    def test_timeshift_offset(self, parser: argparse.ArgumentParser, timeshift_offset: str):
        parsed = parser.parse_args(["--niconico-timeshift-offset", timeshift_offset])
        assert parsed.niconico_timeshift_offset == 123
