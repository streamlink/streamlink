import argparse
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
    hours_minutes_seconds_float,
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
    @pytest.mark.parametrize(
        ("sign", "factor"),
        [
            pytest.param("", 1, id="positive"),
            pytest.param("-", -1, id="negative"),
        ],
    )
    @pytest.mark.parametrize(
        ("timestamp", "as_float", "expected"),
        [
            # decimals
            pytest.param("0", True, 0.0, id="zero"),
            pytest.param("123", True, 123.0, id="decimal without fraction"),
            pytest.param("123.456789", True, 123.456789, id="decimal with fraction"),
            # XX:XX:XX
            pytest.param("0:0", True, 0.0, id="0:0"),
            pytest.param("0:0:0", True, 0.0, id="0:0:0"),
            pytest.param("1:2", True, 62.0, id="X:X"),
            pytest.param("1:2.3", True, 62.3, id="X:X.X"),
            pytest.param("12:34", True, 754.0, id="XX:XX"),
            pytest.param("12:34.56", True, 754.56, id="XX:XX.XX"),
            pytest.param("123:45", True, 7425.0, id="XXX:XX"),
            pytest.param("123:45.67", True, 7425.67, id="XXX:XX.XX"),
            pytest.param("1:2:3", True, 3723.0, id="X:X:X"),
            pytest.param("1:2:3.4", True, 3723.4, id="X:X:X.X"),
            pytest.param("12:34:56", True, 45296.0, id="XX:XX:XX"),
            pytest.param("12:34:56.78", True, 45296.78, id="XX:XX:XX.XX"),
            pytest.param("123:4:5", True, 443045.0, id="XXX:X:X"),
            pytest.param("123:4:5.6", True, 443045.6, id="XXX:X:X.X"),
            # XXhXXmXXs
            pytest.param("0s", True, 0.0, id="0s"),
            pytest.param("0m0s", True, 0.0, id="0m0s"),
            pytest.param("0h0m0s", True, 0.0, id="0h0m0s"),
            pytest.param("1s", True, 1.0, id="Xs"),
            pytest.param("1.2s", True, 1.2, id="X.Xs"),
            pytest.param("12s", True, 12.0, id="XXs"),
            pytest.param("12.3s", True, 12.3, id="XX.Xs"),
            pytest.param("123s", True, 123.0, id="XXXs"),
            pytest.param("123.4s", True, 123.4, id="XXX.Xs"),
            pytest.param("1m", True, 60.0, id="Xm"),
            pytest.param("12m", True, 720.0, id="XXm"),
            pytest.param("123m", True, 7380.0, id="XXXm"),
            pytest.param("1h", True, 3600.0, id="Xh"),
            pytest.param("12h", True, 43200.0, id="XXh"),
            pytest.param("123h", True, 442800.0, id="XXXh"),
            pytest.param("1m2s", True, 62.0, id="XmXs"),
            pytest.param("1m2.3s", True, 62.3, id="XmX.Xs"),
            pytest.param("12m3s", True, 723.0, id="XXmXs"),
            pytest.param("12m3.4s", True, 723.4, id="XXmX.Xs"),
            pytest.param("12m34s", True, 754.0, id="XXmXXs"),
            pytest.param("12m34.5s", True, 754.5, id="XXmXX.Xs"),
            pytest.param("123m45s", True, 7425.0, id="XXXmXXs"),
            pytest.param("123m45.6s", True, 7425.6, id="XXXmXX.Xs"),
            pytest.param("1h2m3s", True, 3723.0, id="XhXmXs"),
            pytest.param("12h34m56s", True, 45296.0, id="XXhXXmXXs"),
            pytest.param("12h34m56.78s", True, 45296.78, id="XXhXXmXX.XXs"),
            pytest.param("123h4m5s", True, 443045.0, id="XXXhXmXs"),
            pytest.param("123h4m5.6s", True, 443045.6, id="XXXhXmX.Xs"),
            pytest.param("1h2s", True, 3602.0, id="XhXs"),
            pytest.param("1h2m", True, 3720.0, id="XhXs"),
            pytest.param("12.34S", True, 12.34, id="XX.XXS"),
            pytest.param("12M34.56S", True, 754.56, id="XXMXX.XXS"),
            pytest.param("12H34M56.78S", True, 45296.78, id="XXHXXMXX.XXS"),
            # integers
            pytest.param("0", False, 0, id="zero (int)"),
            pytest.param("123", False, 123, id="decimal without fraction (int)"),
            pytest.param("123.456789", False, 123, id="decimal with fraction (int)"),
            pytest.param("12:34:56", False, 45296, id="XX:XX:XX (int)"),
            pytest.param("12:34:56.78", False, 45296, id="XX:XX:XX.XX (int)"),
            pytest.param("12h34m56s", False, 45296, id="XXhXXmXXs (int)"),
            pytest.param("12h34m56.78s", False, 45296, id="XXhXXmXX.XXs (int)"),
            # base 10
            pytest.param("0123", True, 123.0, id="base10"),
            pytest.param("08:08:08", True, 29288.0, id="XX:XX:XX base10"),
            pytest.param("08h08m08s", True, 29288.0, id="XXhXXmXXs base10"),
        ],
    )
    def test_hours_minutes_seconds(self, timestamp: str, as_float: bool, sign: str, factor: int, expected: float):
        method = hours_minutes_seconds_float if as_float else hours_minutes_seconds
        res = method(f"{sign}{timestamp}")
        assert type(res) is type(expected)
        assert res == factor * expected

    @pytest.mark.parametrize(
        "timestamp",
        [
            # missing timestamp
            pytest.param("", id="empty"),
            pytest.param(" ", id="whitespace"),
            # invalid numbers
            pytest.param("+123", id="plus sign"),
            pytest.param("1e10", id="exponent notation"),
            pytest.param("1_000", id="digit notation"),
            pytest.param("NaN", id="NaN"),
            pytest.param("infinity", id="infinity"),
            pytest.param("0xff", id="base16"),
            # invalid format
            pytest.param("foo", id="invalid input"),
            pytest.param(" 1:2:3 ", id="untrimmed input"),
            pytest.param(":1:2", id="missing hours value"),
            pytest.param("1::2", id="missing minutes value"),
            pytest.param("1:2:", id="missing seconds value"),
            pytest.param("foo:1:2", id="invalid hours"),
            pytest.param("1:foo:2", id="invalid minutes"),
            pytest.param("1:2:foo", id="invalid seconds"),
            pytest.param("1:60", id="seconds with two digits gte 60"),
            pytest.param("1:60:59", id="minutes with two digits gte 60"),
            pytest.param("1:234", id="minutes and seconds with three digits"),
            pytest.param("1:234:56", id="hours and minutes with three digits"),
            pytest.param("1:23:456", id="hours and seconds with three digits"),
            pytest.param("1h2", id="missing minutes or seconds suffix"),
            pytest.param("1m2", id="missing seconds suffix"),
            pytest.param("1.2h", id="hours fraction"),
            pytest.param("1.2m", id="minutes fraction"),
            pytest.param("1:2s", id="mixed format"),
            pytest.param("1h2:3", id="mixed format"),
            pytest.param("1:2:3s", id="mixed format"),
            pytest.param("1:2m3s", id="mixed format"),
        ],
    )
    def test_hours_minutes_seconds_exception(self, timestamp: str):
        with pytest.raises(ValueError):  # noqa: PT011
            hours_minutes_seconds_float(timestamp)

    @pytest.mark.parametrize("method", [hours_minutes_seconds, hours_minutes_seconds_float])
    def test_hours_minutes_seconds_argparse_failure(self, method):
        parser = argparse.ArgumentParser(exit_on_error=False)
        parser.add_argument("hms", type=method)
        with pytest.raises(argparse.ArgumentError) as exc_info:
            parser.parse_args(["invalid"])
        assert str(exc_info.value) == "argument hms: invalid hours_minutes_seconds value: 'invalid'", \
            "has the correct method name, so argparse errors are useful"  # fmt: skip

    def test_hours_minutes_seconds_hashable(self):
        assert hash(hours_minutes_seconds) != hash(hours_minutes_seconds_float)

    def test_seconds_to_hhmmss(self):
        assert seconds_to_hhmmss(0) == "00:00:00"
        assert seconds_to_hhmmss(1) == "00:00:01"
        assert seconds_to_hhmmss(60) == "00:01:00"
        assert seconds_to_hhmmss(3600) == "01:00:00"

        assert seconds_to_hhmmss(13997) == "03:53:17"
        assert seconds_to_hhmmss(13997.4) == "03:53:17.4"
