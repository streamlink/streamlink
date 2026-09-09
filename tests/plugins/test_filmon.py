from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from unittest.mock import Mock

import freezegun
import pytest

from streamlink.plugins.filmon import Filmon, FilmOnAPI, FilmOnHLS
from tests.plugins import PluginCanHandleUrl


if TYPE_CHECKING:
    from streamlink import Streamlink


class TestPluginCanHandleUrlFilmon(PluginCanHandleUrl):
    __plugin__ = Filmon

    should_match_groups = [
        ("https://filmon.com/v2/tv/bbc-news", {"alias": "bbc-news"}),
        ("https://filmon.tv/v2/tv/bbc-news", {"alias": "bbc-news"}),
        ("https://filmon.com/tv/bbc-news", {"alias": "bbc-news"}),
        ("https://filmon.tv/tv/bbc-news", {"alias": "bbc-news"}),
    ]


class TestFilmOnHLS:
    @pytest.fixture(autouse=True)
    def frozen_time(self):
        with freezegun.freeze_time("1970-01-01T00:00:00Z") as frozen_time:
            yield frozen_time

    @pytest.fixture(autouse=True)
    def get_stream_data(self, monkeypatch: pytest.MonkeyPatch):
        mock = Mock(
            side_effect=[
                [
                    ("high", "http://fake/playlist.m3u8?id=456", 30.0),
                    ("low", "http://fake/playlist.m3u8?id=def", 30.0),
                ],
                [
                    ("high", "http://fake/playlist.m3u8?id=789", 30.0),
                    ("low", "http://fake/playlist.m3u8?id=ghi", 30.0),
                ],
            ],
        )
        monkeypatch.setattr(FilmOnAPI, "get_stream_data", mock)
        return mock

    @pytest.fixture()
    def filmonhls(self, session: Streamlink):
        return FilmOnHLS(
            session,
            "http://fake/720p.m3u8?id=123",
            api=FilmOnAPI(session),
            channel="test",
            quality="high",
            watch_timeout=30.0,
        )

    def test_to_url(self, filmonhls: FilmOnHLS):
        assert filmonhls.to_url() == "http://fake/720p.m3u8?id=123"

    def test_to_url_updated(self, filmonhls: FilmOnHLS, frozen_time):
        assert filmonhls.to_url() == "http://fake/720p.m3u8?id=123"

        frozen_time.move_to(datetime.fromtimestamp(filmonhls._next_reload, tz=timezone.utc))
        assert filmonhls.to_url() == "http://fake/720p.m3u8?id=456"

        frozen_time.move_to(datetime.fromtimestamp(filmonhls._next_reload, tz=timezone.utc))
        assert filmonhls.to_url() == "http://fake/720p.m3u8?id=789"

    def test_to_url_missing_quality(self, filmonhls: FilmOnHLS, frozen_time):
        filmonhls.quality = "doesnotexist"
        frozen_time.move_to(datetime.fromtimestamp(filmonhls._next_reload, tz=timezone.utc))
        with pytest.raises(TypeError) as cm:
            filmonhls.to_url()
        assert str(cm.value) == "Stream has expired and cannot be translated to a URL"
