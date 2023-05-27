from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, Union

import pytest

from streamlink.stream.hls_playlist import (
    ByteRange,
    DateRange,
    ExtInf,
    M3U8Parser,
    Media,
    Resolution,
    Segment,
    StreamInfo,
    load,
)
from tests.resources import text


UTC = timezone.utc


def test_parse_tag_callback_cache():
    class M3U8ParserSubclass(M3U8Parser):
        def parse_tag_foo_bar(self):  # pragma: no cover
            pass

    parent = M3U8Parser()
    assert hasattr(parent, "_TAGS")
    assert "EXT-X-VERSION" in parent._TAGS

    childA = M3U8ParserSubclass()
    assert hasattr(childA, "_TAGS")
    assert "FOO-BAR" in childA._TAGS

    childB = M3U8ParserSubclass()
    assert hasattr(childB, "_TAGS")
    assert "FOO-BAR" in childB._TAGS

    assert parent._TAGS is not childA._TAGS
    assert childA._TAGS is childB._TAGS


@pytest.mark.parametrize(("string", "expected"), [
    ("", (None, None)),
    ("invalid", (None, None)),
    ("#TAG", ("TAG", "")),
    ("#TAG:ATTRIBUTES", ("TAG", "ATTRIBUTES")),
    ("#TAG:    ATTRIBUTES    ", ("TAG", "ATTRIBUTES")),
])
def test_split_tag(string: str, expected: Union[Tuple[str, str], Tuple[None, None]]):
    assert M3U8Parser.split_tag(string) == expected


@pytest.mark.parametrize(("attributes", "log", "expected"), [
    pytest.param("", False, {}, id="empty attribute list"),
    pytest.param("invalid", True, {}, id="invalid attribute list"),
    pytest.param("?=VALUE", True, {}, id="invalid attribute name"),
    pytest.param("key=VALUE", True, {}, id="lowercase attribute name"),
    pytest.param("KEY = VALUE", True, {}, id="invalid attribute format"),
    pytest.param("KEY=", True, {}, id="missing attribute value"),
    pytest.param("KEY=\"", True, {}, id="invalid attribute value"),
    pytest.param("KEY=123", False, {"KEY": "123"}, id="decimal integer"),
    pytest.param("KEY=0xdeadbeef", False, {"KEY": "0xdeadbeef"}, id="hexadecimal sequence, lowercase"),
    pytest.param("KEY=0XDEADBEEF", False, {"KEY": "0XDEADBEEF"}, id="hexadecimal sequence, uppercase"),
    pytest.param("KEY=123.456", False, {"KEY": "123.456"}, id="decimal floating point number"),
    pytest.param("KEY=-123.456", False, {"KEY": "-123.456"}, id="signed decimal floating point number"),
    pytest.param("KEY=\"\"", False, {"KEY": ""}, id="empty quoted string"),
    pytest.param("KEY=\"foobar\"", False, {"KEY": "foobar"}, id="quoted string"),
    pytest.param("KEY=\"foo\"bar\"", True, {}, id="invalid quoted string (quote)"),
    pytest.param("KEY=\"foo\rbar\"", True, {}, id="invalid quoted string (carriage return)"),
    pytest.param("KEY=\"foo\nbar\"", True, {}, id="invalid quoted string (new line)"),
    pytest.param("KEY=VALUE", False, {"KEY": "VALUE"}, id="enumerated string"),
    pytest.param("KEY=<@_@>", False, {"KEY": "<@_@>"}, id="enumerated string with special characters"),
    pytest.param("KEY=1920x1080", False, {"KEY": "1920x1080"}, id="decimal resolution"),
    pytest.param("KEY-123=VALUE", False, {"KEY-123": "VALUE"}, id="attribute name with alphanumerical chars and dashes"),
    pytest.param(
        "A=123,B=0xdeadbeef,C=123.456,D=-123.456,E=\"value, value, value\",F=VALUE,G=1920x1080",
        False,
        {
            "A": "123",
            "B": "0xdeadbeef",
            "C": "123.456",
            "D": "-123.456",
            "E": "value, value, value",
            "F": "VALUE",
            "G": "1920x1080",
        },
        id="multiple attributes",
    ),
    pytest.param(
        "A=\"foo\", B=123 , C=VALUE,D=456 ",
        False,
        {"A": "foo", "B": "123", "C": "VALUE", "D": "456"},
        id="multiple attributes with surrounding spaces (off-spec)",
    ),
    pytest.param(
        "A=\"foo\"B=123",
        True,
        {},
        id="multiple attributes with invalid format (missing commas)",
    ),
    pytest.param(
        "A=\"foo\",B = 123",
        True,
        {},
        id="multiple attributes with invalid format (spaces)",
    ),
    pytest.param(
        "A=\"foo\",B=",
        True,
        {},
        id="multiple attributes with invalid format (missing value)",
    ),
])
def test_parse_attributes(caplog: pytest.LogCaptureFixture, attributes: str, log: bool, expected: dict):
    assert M3U8Parser.parse_attributes(attributes) == expected
    assert [(r.module, r.levelname, r.message) for r in caplog.records] == ([
        ("hls_playlist", "warning", "Discarded invalid attributes list"),
    ] if log else [])


@pytest.mark.parametrize(("string", "expected"), [
    ("", False),
    ("NO", False),
    ("YES", True),
])
def test_parse_bool(string: str, expected: bool):
    assert M3U8Parser.parse_bool(string) is expected


@pytest.mark.parametrize(("string", "expected"), [
    ("", None),
    ("invalid", None),
    ("1234", ByteRange(1234, None)),
    ("1234@5678", ByteRange(1234, 5678)),
])
def test_parse_byterange(string: str, expected: Optional[ByteRange]):
    assert M3U8Parser.parse_byterange(string) == expected


@pytest.mark.parametrize(("string", "expected"), [
    ("", ExtInf(0, None)),
    ("invalid", ExtInf(0, None)),
    ("123", ExtInf(123.0, None)),
    ("123.456", ExtInf(123.456, None)),
    ("123.456,foo", ExtInf(123.456, "foo")),
])
def test_parse_extinf(string: str, expected: ExtInf):
    assert M3U8Parser.parse_extinf(string) == expected


@pytest.mark.parametrize(("string", "log", "expected"), [
    (None, False, None),
    ("", True, None),
    ("deadbeef", True, None),
    ("0xnothex", True, None),
    ("0xdeadbeef", False, b"\xde\xad\xbe\xef"),
    ("0XDEADBEEF", False, b"\xde\xad\xbe\xef"),
    ("0xdeadbee", False, b"\x0d\xea\xdb\xee"),
])
def test_parse_hex(caplog: pytest.LogCaptureFixture, string: Optional[str], log: bool, expected: Optional[bytes]):
    assert M3U8Parser.parse_hex(string) == expected
    assert [(r.module, r.levelname, r.message) for r in caplog.records] == ([
        ("hls_playlist", "warning", "Discarded invalid hexadecimal-sequence attribute value"),
    ] if log else [])


@pytest.mark.parametrize(("string", "log", "expected"), [
    (None, False, None),
    ("not an ISO8601 string", True, None),
    ("2000-01-01", True, None),
    ("2000-99-99T99:99:99.999Z", True, None),
    ("2000-01-01T00:00:00.000Z", False, datetime(2000, 1, 1, 0, 0, 0, 0, tzinfo=UTC)),
])
def test_parse_iso8601(caplog: pytest.LogCaptureFixture, string: Optional[str], log: bool, expected: Optional[datetime]):
    assert M3U8Parser.parse_iso8601(string) == expected
    assert [(r.module, r.levelname, r.message) for r in caplog.records] == ([
        ("hls_playlist", "warning", "Discarded invalid ISO8601 attribute value"),
    ] if log else [])


@pytest.mark.parametrize(("string", "expected"), [
    (None, None),
    ("123", timedelta(seconds=123.0)),
    ("123.456", timedelta(seconds=123.456)),
    ("-123.456", timedelta(seconds=-123.456)),
])
def test_parse_timedelta(string: Optional[str], expected: Optional[timedelta]):
    assert M3U8Parser.parse_timedelta(string) == expected


@pytest.mark.parametrize(("string", "expected"), [
    ("", Resolution(0, 0)),
    ("invalid", Resolution(0, 0)),
    ("1920x1080", Resolution(1920, 1080)),
])
def test_parse_resolution(string: str, expected: Resolution):
    assert M3U8Parser.parse_resolution(string) == expected


class TestHLSPlaylist:
    def test_load(self):
        with text("hls/test_1.m3u8") as m3u8_fh:
            playlist = load(m3u8_fh.read(), "http://test.se/")

        assert playlist.media == [
            Media(
                uri="http://test.se/audio/stereo/en/128kbit.m3u8",
                type="AUDIO",
                group_id="stereo",
                language="en",
                name="English",
                default=True,
                autoselect=True,
                forced=False,
                characteristics=None,
            ),
            Media(
                uri="http://test.se/audio/stereo/none/128kbit.m3u8",
                type="AUDIO",
                group_id="stereo",
                language="dubbing",
                name="Dubbing",
                default=False,
                autoselect=True,
                forced=False,
                characteristics=None,
            ),
            Media(
                uri="http://test.se/audio/surround/en/320kbit.m3u8",
                type="AUDIO",
                group_id="surround",
                language="en",
                name="English",
                default=True,
                autoselect=True,
                forced=False,
                characteristics=None,
            ),
            Media(
                uri="http://test.se/audio/stereo/none/128kbit.m3u8",
                type="AUDIO",
                group_id="surround",
                language="dubbing",
                name="Dubbing",
                default=False,
                autoselect=True,
                forced=False,
                characteristics=None,
            ),
            Media(
                uri="http://test.se/subtitles_de.m3u8",
                type="SUBTITLES",
                group_id="subs",
                language="de",
                name="Deutsch",
                default=False,
                autoselect=True,
                forced=False,
                characteristics=None,
            ),
            Media(
                uri="http://test.se/subtitles_en.m3u8",
                type="SUBTITLES",
                group_id="subs",
                language="en",
                name="English",
                default=True,
                autoselect=True,
                forced=False,
                characteristics=None,
            ),
            Media(
                uri="http://test.se/subtitles_es.m3u8",
                type="SUBTITLES",
                group_id="subs",
                language="es",
                name="Espanol",
                default=False,
                autoselect=True,
                forced=False,
                characteristics=None,
            ),
            Media(
                uri="http://test.se/subtitles_fr.m3u8",
                type="SUBTITLES",
                group_id="subs",
                language="fr",
                name="Français",
                default=False,
                autoselect=True,
                forced=False,
                characteristics=None,
            ),
        ]

        assert [p.stream_info for p in playlist.playlists] == [
            StreamInfo(
                bandwidth=260000,
                program_id="1",
                codecs=["avc1.4d400d", "mp4a.40.2"],
                resolution=Resolution(width=422, height=180),
                audio="stereo",
                video=None,
                subtitles="subs",
            ),
            StreamInfo(
                bandwidth=520000,
                program_id="1",
                codecs=["avc1.4d4015", "mp4a.40.2"],
                resolution=Resolution(width=638, height=272),
                audio="stereo",
                video=None,
                subtitles="subs",
            ),
            StreamInfo(
                bandwidth=830000,
                program_id="1",
                codecs=["avc1.4d4015", "mp4a.40.2"],
                resolution=Resolution(width=638, height=272),
                audio="stereo",
                video=None,
                subtitles="subs",
            ),
            StreamInfo(
                bandwidth=1100000,
                program_id="1",
                codecs=["avc1.4d401f", "mp4a.40.2"],
                resolution=Resolution(width=958, height=408),
                audio="surround",
                video=None,
                subtitles="subs",
            ),
            StreamInfo(
                bandwidth=1600000,
                program_id="1",
                codecs=["avc1.4d401f", "mp4a.40.2"],
                resolution=Resolution(width=1277, height=554),
                audio="surround",
                video=None,
                subtitles="subs",
            ),
            StreamInfo(
                bandwidth=4100000,
                program_id="1",
                codecs=["avc1.4d4028", "mp4a.40.2"],
                resolution=Resolution(width=1921, height=818),
                audio="surround",
                video=None,
                subtitles="subs",
            ),
            StreamInfo(
                bandwidth=6200000,
                program_id="1",
                codecs=["avc1.4d4028", "mp4a.40.2"],
                resolution=Resolution(width=1921, height=818),
                audio="surround",
                video=None,
                subtitles="subs",
            ),
            StreamInfo(
                bandwidth=10000000,
                program_id="1",
                codecs=["avc1.4d4033", "mp4a.40.2"],
                resolution=Resolution(width=4096, height=1744),
                audio="surround",
                video=None,
                subtitles="subs",
            ),
        ]

    def test_parse_date(self):
        with text("hls/test_date.m3u8") as m3u8_fh:
            playlist = load(m3u8_fh.read(), "http://test.se/")

        start_date = datetime(year=2000, month=1, day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=UTC)
        end_date = datetime(year=2000, month=1, day=1, hour=0, minute=1, second=0, microsecond=0, tzinfo=UTC)
        delta_15 = timedelta(seconds=15)
        delta_30 = timedelta(seconds=30, milliseconds=500)
        delta_60 = timedelta(seconds=60)

        assert playlist.targetduration == 120

        assert list(playlist.dateranges) == [
            DateRange(
                id="start-invalid",
                start_date=None,
                classname=None,
                end_date=None,
                duration=None,
                planned_duration=None,
                end_on_next=False,
                x={},
            ),
            DateRange(
                id="start-no-frac",
                start_date=start_date,
                classname=None,
                end_date=None,
                duration=None,
                planned_duration=None,
                end_on_next=False,
                x={},
            ),
            DateRange(
                id="start-with-frac",
                start_date=start_date,
                classname=None,
                end_date=None,
                duration=None,
                planned_duration=None,
                end_on_next=False,
                x={},
            ),
            DateRange(
                id="with-class",
                start_date=start_date,
                classname="bar",
                end_date=None,
                duration=None,
                planned_duration=None,
                end_on_next=False,
                x={},
            ),
            DateRange(
                id="duration",
                start_date=start_date,
                duration=delta_30,
                classname=None,
                end_date=None,
                planned_duration=None,
                end_on_next=False,
                x={},
            ),
            DateRange(
                id="planned-duration",
                start_date=start_date,
                planned_duration=delta_15,
                classname=None,
                end_date=None,
                duration=None,
                end_on_next=False,
                x={},
            ),
            DateRange(
                id="duration-precedence",
                start_date=start_date,
                duration=delta_30,
                planned_duration=delta_15,
                classname=None,
                end_date=None,
                end_on_next=False,
                x={},
            ),
            DateRange(
                id="end",
                start_date=start_date,
                end_date=end_date,
                classname=None,
                duration=None,
                planned_duration=None,
                end_on_next=False,
                x={},
            ),
            DateRange(
                id="end-precedence",
                start_date=start_date,
                end_date=end_date,
                duration=delta_30,
                classname=None,
                planned_duration=None,
                end_on_next=False,
                x={},
            ),
            DateRange(
                id=None,
                start_date=None,
                end_date=None,
                duration=None,
                classname=None,
                planned_duration=None,
                end_on_next=False,
                x={"X-CUSTOM": "value"},
            ),
        ]
        assert list(playlist.segments) == [
            Segment(
                uri="http://test.se/segment0-15.ts",
                duration=15.0,
                title="live",
                date=start_date,
                key=None,
                discontinuity=False,
                byterange=None,
                map=None,
            ),
            Segment(
                uri="http://test.se/segment15-30.5.ts",
                duration=15.5,
                title="live",
                date=start_date + delta_15,
                key=None,
                discontinuity=False,
                byterange=None,
                map=None,
            ),
            Segment(
                uri="http://test.se/segment30.5-60.ts",
                duration=29.5,
                title="live",
                date=start_date + delta_30,
                key=None,
                discontinuity=False,
                byterange=None,
                map=None,
            ),
            Segment(
                uri="http://test.se/segment60-.ts",
                duration=60.0,
                title="live",
                date=start_date + delta_60,
                key=None,
                discontinuity=False,
                byterange=None,
                map=None,
            ),
        ]

        assert [playlist.is_date_in_daterange(playlist.segments[0].date, daterange) for daterange in playlist.dateranges] \
               == [None, True, True, True, True, True, True, True, True, None]
        assert [playlist.is_date_in_daterange(playlist.segments[1].date, daterange) for daterange in playlist.dateranges] \
               == [None, True, True, True, True, False, True, True, True, None]
        assert [playlist.is_date_in_daterange(playlist.segments[2].date, daterange) for daterange in playlist.dateranges] \
               == [None, True, True, True, False, False, False, True, True, None]
        assert [playlist.is_date_in_daterange(playlist.segments[3].date, daterange) for daterange in playlist.dateranges] \
               == [None, True, True, True, False, False, False, False, False, None]
