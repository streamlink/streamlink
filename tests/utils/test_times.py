from datetime import datetime, timedelta, timezone

import freezegun
import isodate  # type: ignore[import]
import pytest

from streamlink.utils.times import (
    LOCAL,
    UTC,
    fromlocaltimestamp,
    fromtimestamp,
    hours_minutes_seconds,
    localnow,
    now,
    parse_datetime,
    seconds_to_hhmmss,
)


class TestDatetime:
    TS_Y2K = 946684800

    @pytest.fixture()
    def chatham_islands(self, monkeypatch: pytest.MonkeyPatch):
        chatham_islands = timezone(timedelta(hours=12, minutes=45))
        monkeypatch.setattr("streamlink.utils.times.LOCAL", chatham_islands)
        return chatham_islands

    def test_constants(self):
        assert UTC is timezone.utc
        assert LOCAL is isodate.LOCAL

    def test_now(self):
        with freezegun.freeze_time("2000-01-01T00:00:00Z"):
            assert now() == datetime(2000, 1, 1, 0, 0, 0, 0, timezone.utc)

    def test_localnow(self, chatham_islands: timezone):
        with freezegun.freeze_time("2000-01-01T00:00:00+1245"):
            assert localnow() == datetime(2000, 1, 1, 0, 0, 0, 0, chatham_islands)

    def test_fromtimestamp(self):
        assert fromtimestamp(self.TS_Y2K) == datetime(2000, 1, 1, 0, 0, 0, 0, timezone.utc)

    def test_fromlocaltimestamp(self, chatham_islands: timezone):
        assert fromlocaltimestamp(self.TS_Y2K) == datetime(2000, 1, 1, 12, 45, 0, 0, chatham_islands)
        assert fromlocaltimestamp(self.TS_Y2K) == datetime(2000, 1, 1, 0, 0, 0, 0, timezone.utc)

    def test_parse_datetime(self, chatham_islands: timezone):
        assert parse_datetime("2000-01-01T00:00:00") == datetime(2000, 1, 1, 0, 0, 0, 0)  # noqa: DTZ001
        assert parse_datetime("2000-01-01T00:00:00Z") == datetime(2000, 1, 1, 0, 0, 0, 0, timezone.utc)
        assert parse_datetime("2000-01-01T00:00:00+1245") == datetime(2000, 1, 1, 0, 0, 0, 0, chatham_islands)
        with pytest.raises(isodate.ISO8601Error):
            parse_datetime("2000-01-01")


class TestHoursMinutesSeconds:
    def test_hours_minutes_seconds(self):
        assert hours_minutes_seconds("00:01:30") == 90
        assert hours_minutes_seconds("01:20:15") == 4815
        assert hours_minutes_seconds("26:00:00") == 93600

        assert hours_minutes_seconds("07") == 7
        assert hours_minutes_seconds("444") == 444
        assert hours_minutes_seconds("8888") == 8888

        assert hours_minutes_seconds("01h") == 3600
        assert hours_minutes_seconds("01h22m33s") == 4953
        assert hours_minutes_seconds("01H22M37S") == 4957
        assert hours_minutes_seconds("01h30s") == 3630
        assert hours_minutes_seconds("1m33s") == 93
        assert hours_minutes_seconds("55s") == 55

        assert hours_minutes_seconds("-00:01:40") == 100
        assert hours_minutes_seconds("-00h02m30s") == 150

        assert hours_minutes_seconds("02:04") == 124
        assert hours_minutes_seconds("1:10") == 70
        assert hours_minutes_seconds("10:00") == 600

        with pytest.raises(ValueError):  # noqa: PT011
            hours_minutes_seconds("FOO")
        with pytest.raises(ValueError):  # noqa: PT011
            hours_minutes_seconds("BAR")
        with pytest.raises(ValueError):  # noqa: PT011
            hours_minutes_seconds("11:ERR:00")

    def test_seconds_to_hhmmss(self):
        assert seconds_to_hhmmss(0) == "00:00:00"
        assert seconds_to_hhmmss(1) == "00:00:01"
        assert seconds_to_hhmmss(60) == "00:01:00"
        assert seconds_to_hhmmss(3600) == "01:00:00"

        assert seconds_to_hhmmss(13997) == "03:53:17"
        assert seconds_to_hhmmss(13997.4) == "03:53:17.4"
