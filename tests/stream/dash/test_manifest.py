import datetime
import itertools
from contextlib import nullcontext
from unittest.mock import Mock

import pytest
from freezegun import freeze_time

from streamlink.stream.dash.manifest import MPD, DASHSegment, MPDParsers, MPDParsingError, Representation
from streamlink.utils.times import fromtimestamp
from tests.resources import xml


EPOCH_START = fromtimestamp(0)
UTC = datetime.timezone.utc


class TestSegment:
    @pytest.mark.parametrize(
        ("segmentdata", "expected"),
        [
            ({"uri": "https://foo/bar", "num": 123, "duration": 0.0, "init": True, "content": False}, "initialization"),
            ({"uri": "https://foo/bar", "num": 123, "duration": 0.0, "init": True, "content": True}, "123"),
            ({"uri": "https://foo/bar", "num": -1, "duration": 0.0, "init": True, "content": True}, "bar"),
            ({"uri": "https://foo/bar", "num": 123, "duration": 0.0}, "123"),
            ({"uri": "https://foo/bar", "num": -1, "duration": 0.0}, "bar"),
            ({"uri": "https://foo/bar/", "num": -1, "duration": 0.0}, "bar"),
            ({"uri": "https://foo/bar/baz.qux", "num": -1, "duration": 0.0}, "baz.qux"),
            ({"uri": "https://foo/bar/baz.qux?asdf", "num": -1, "duration": 0.0}, "baz.qux"),
        ],
    )
    def test_name(self, segmentdata: dict, expected: str):
        segment = DASHSegment(**segmentdata)
        assert segment.name == expected

    @pytest.mark.parametrize(
        ("available_at", "expected"),
        [
            (datetime.datetime(2000, 1, 2, 3, 4, 5, 123456, tzinfo=UTC), 1 * 86400 + 3 * 3600 + 4 * 60 + 5 + 0.123456),
            (datetime.datetime(2000, 1, 1, 0, 0, 0, 0, tzinfo=UTC), 0.0),
            (datetime.datetime(1999, 12, 31, 23, 59, 59, 999999, tzinfo=UTC), 0.0),
        ],
    )
    def test_available_in(self, available_at: datetime.datetime, expected: float):
        segment = DASHSegment(
            uri="foo",
            num=-1,
            duration=0.0,
            available_at=available_at,
        )
        with freeze_time("2000-01-01T00:00:00Z"):
            assert segment.available_in == pytest.approx(expected)

    def test_availability(self):
        segment = DASHSegment(
            uri="foo",
            num=-1,
            duration=0.0,
            available_at=datetime.datetime(2000, 1, 2, 3, 4, 5, 123456, tzinfo=UTC),
        )
        with freeze_time("2000-01-01T00:00:00Z"):
            assert segment.availability == "2000-01-02T03:04:05.123456Z / 2000-01-01T00:00:00.000000Z"


class TestMPDParsers:
    def test_bool_str(self):
        assert MPDParsers.bool_str("true")
        assert MPDParsers.bool_str("TRUE")
        assert MPDParsers.bool_str("True")

        assert not MPDParsers.bool_str("0")
        assert not MPDParsers.bool_str("False")
        assert not MPDParsers.bool_str("false")
        assert not MPDParsers.bool_str("FALSE")

    def test_type(self):
        assert MPDParsers.type("dynamic") == "dynamic"
        assert MPDParsers.type("static") == "static"
        with pytest.raises(MPDParsingError):
            # noinspection PyTypeChecker
            MPDParsers.type("other")

    def test_duration(self):
        assert MPDParsers.duration()("PT1S") == datetime.timedelta(seconds=1)
        assert MPDParsers.duration()("P1W") == datetime.timedelta(seconds=7 * 24 * 3600)

        assert MPDParsers.duration(EPOCH_START)("P3M") == datetime.timedelta(days=31 + 28 + 31)
        assert MPDParsers.duration(EPOCH_START + datetime.timedelta(31))("P3M") == datetime.timedelta(days=28 + 31 + 30)

        assert MPDParsers.duration(EPOCH_START)("P3Y") == datetime.timedelta(days=3 * 365 + 1)
        assert MPDParsers.duration(EPOCH_START + datetime.timedelta(3 * 365))("P3Y") == datetime.timedelta(days=3 * 365)

        with freeze_time(EPOCH_START):
            assert MPDParsers.duration()("P3M") == datetime.timedelta(days=31 + 28 + 31)
            assert MPDParsers.duration()("P3Y") == datetime.timedelta(days=3 * 365 + 1)

    def test_datetime(self):
        assert MPDParsers.datetime("2018-01-01T00:00:00Z") == datetime.datetime(2018, 1, 1, 0, 0, 0, tzinfo=UTC)

    def test_segment_template(self):
        assert MPDParsers.segment_template("$Time$-$Number$-$Other$")(Time=1, Number=2, Other=3) == "1-2-3"
        assert MPDParsers.segment_template("$Number%05d$")(Number=123) == "00123"
        assert MPDParsers.segment_template("$Time%0.02f$")(Time=100.234) == "100.23"

    def test_frame_rate(self):
        assert MPDParsers.frame_rate("1/25") == pytest.approx(1.0 / 25.0)
        assert MPDParsers.frame_rate("0.2") == pytest.approx(0.2)

    def test_timedelta(self):
        assert MPDParsers.timedelta(1)(100) == datetime.timedelta(0, 100.0)
        assert MPDParsers.timedelta(10)(100) == datetime.timedelta(0, 10.0)

    def test_range(self):
        assert MPDParsers.range("100-") == (100, None)
        assert MPDParsers.range("100-199") == (100, 100)
        with pytest.raises(MPDParsingError):
            MPDParsers.range("100")


class TestMPDParser:
    @pytest.mark.parametrize(
        ("min_buffer_time", "expected"),
        [
            pytest.param("PT1S", 3.0, id="minBufferTime lower than suggestedPresentationDelay"),
            pytest.param("PT5S", 5.0, id="minBufferTime greater than suggestedPresentationDelay"),
        ],
    )
    def test_suggested_presentation_delay(self, min_buffer_time: str, expected: float):
        with xml("dash/test_suggested_presentation_delay.mpd") as mpd_xml:
            mpd_xml.attrib["minBufferTime"] = min_buffer_time
            mpd = MPD(mpd_xml, base_url="http://test/", url="http://test/manifest.mpd")
        assert mpd.suggestedPresentationDelay.total_seconds() == expected

    def test_no_segment_list_or_template(self):
        with xml("dash/test_no_segment_list_or_template.mpd") as mpd_xml:
            mpd = MPD(mpd_xml, base_url="http://test/", url="http://test/manifest.mpd")
            segments = [
                {
                    "ident": representation.ident,
                    "mimeType": representation.mimeType,
                    "segments": [
                        (segment.uri, segment.num, segment.duration, segment.available_at, segment.init, segment.content)
                        for segment in itertools.islice(representation.segments(), 100)
                    ],
                }
                for adaptationset in mpd.periods[0].adaptationSets
                for representation in adaptationset.representations
                if representation.id in ("1", "5", "6")
            ]
        availability = datetime.datetime(1970, 1, 1, 0, 0, 0, tzinfo=UTC)

        assert segments == [
            {
                "ident": (None, None, "1"),
                "mimeType": "audio/mp4",
                "segments": [("http://cdn1.example.com/7657412348.mp4", -1, 3256.0, availability, True, True)],
            },
            {
                "ident": (None, None, "5"),
                "mimeType": "application/ttml+xml",
                "segments": [("http://cdn1.example.com/796735657.xml", -1, 3256.0, availability, True, True)],
            },
            {
                "ident": (None, None, "6"),
                "mimeType": "video/mp4",
                "segments": [("http://cdn1.example.com/8563456473.mp4", -1, 3256.0, availability, True, True)],
            },
        ]

    def test_segments_number_time(self):
        with xml("dash/test_1.mpd") as mpd_xml:
            mpd = MPD(mpd_xml, base_url="http://test.se/", url="http://test.se/manifest.mpd")

            segments = mpd.periods[0].adaptationSets[0].representations[0].segments()
            init_segment = next(segments)
            assert init_segment.uri == "http://test.se/tracks-v3/init-1526842800.g_m4v"

            # suggested delay is 11 seconds, each segment is 5 seconds long - so there should be 3
            assert [segment.uri for segment in itertools.islice(segments, 5)] == [
                "http://test.se/tracks-v3/dvr-1526842800-698.g_m4v?t=3403000",
                "http://test.se/tracks-v3/dvr-1526842800-699.g_m4v?t=3408000",
                "http://test.se/tracks-v3/dvr-1526842800-700.g_m4v?t=3413000",
            ]

    def test_segments_static_number(self):
        with xml("dash/test_2.mpd") as mpd_xml:
            mpd = MPD(mpd_xml, base_url="http://test.se/", url="http://test.se/manifest.mpd")

            segments = mpd.periods[0].adaptationSets[3].representations[0].segments()
            init_segment = next(segments)
            assert init_segment.uri == "http://test.se/video/250kbit/init.mp4"

            video_segments = [segment.uri for segment in itertools.islice(segments, 100000)]
            assert len(video_segments) == 444
            assert video_segments[:5] == [
                "http://test.se/video/250kbit/segment_1.m4s",
                "http://test.se/video/250kbit/segment_2.m4s",
                "http://test.se/video/250kbit/segment_3.m4s",
                "http://test.se/video/250kbit/segment_4.m4s",
                "http://test.se/video/250kbit/segment_5.m4s",
            ]

    def test_segments_dynamic_time(self):
        with xml("dash/test_3.mpd") as mpd_xml:
            mpd = MPD(mpd_xml, base_url="http://test.se/", url="http://test.se/manifest.mpd")

            segments = mpd.periods[0].adaptationSets[0].representations[0].segments()
            init_segment = next(segments)
            assert init_segment.uri == "http://test.se/video-2800000-0.mp4?z32="

            # default suggested delay is 3 seconds, each segment is 4 seconds long - so there should be 1 segment
            assert [segment.uri for segment in itertools.islice(segments, 3)] == [
                "http://test.se/video-time=1525450872000-2800000-0.m4s?z32=",
            ]

    # access manifest one hour after its availabilityStartTime
    @pytest.mark.parametrize(
        ("frozen_time", "timestamp"),
        [
            pytest.param(
                freeze_time("2000-01-01T01:00:00Z"),
                None,
                id="Without explicit timestamp",
            ),
            pytest.param(
                nullcontext(),
                datetime.datetime(2000, 1, 1, 1, 0, 0, 0, tzinfo=UTC),
                id="With explicit timestamp",
            ),
        ],
    )
    def test_segments_dynamic_number(self, frozen_time, timestamp):
        with xml("dash/test_segments_dynamic_number.mpd") as mpd_xml, frozen_time:
            mpd = MPD(mpd_xml, base_url="http://test/", url="http://test/manifest.mpd")
            segments_iterator = mpd.periods[0].adaptationSets[0].representations[0].segments(timestamp=timestamp)
            stream_urls = [(segment.uri, segment.available_at) for segment in itertools.islice(segments_iterator, 4)]

        assert stream_urls == [
            (
                "http://test/hd-5-init.mp4",
                datetime.datetime(2000, 1, 1, 0, 1, 30, tzinfo=UTC),
            ),
            (
                "http://test/hd-5_000000793.mp4",
                datetime.datetime(2000, 1, 1, 0, 59, 15, tzinfo=UTC),
            ),
            (
                "http://test/hd-5_000000794.mp4",
                datetime.datetime(2000, 1, 1, 0, 59, 20, tzinfo=UTC),
            ),
            (
                "http://test/hd-5_000000795.mp4",
                datetime.datetime(2000, 1, 1, 0, 59, 25, tzinfo=UTC),
            ),
        ]

    def test_static_no_publish_time(self):
        with xml("dash/test_static_no_publish_time.mpd") as mpd_xml:
            mpd = MPD(mpd_xml, base_url="http://test/", url="http://test/manifest.mpd")

        segments = mpd.periods[0].adaptationSets[1].representations[0].segments()
        segment_urls = [(segment.uri, segment.available_at) for segment in itertools.islice(segments, 4)]
        # ignores period start time in static manifests
        expected_availability = datetime.datetime(2020, 1, 1, 0, 0, 0, tzinfo=UTC)

        assert segment_urls == [
            ("http://test/dash/150633-video_eng=194000.dash", expected_availability),
            ("http://test/dash/150633-video_eng=194000-0.dash", expected_availability),
            ("http://test/dash/150633-video_eng=194000-2000.dash", expected_availability),
            ("http://test/dash/150633-video_eng=194000-4000.dash", expected_availability),
        ]

    @pytest.mark.parametrize(
        ("manifest", "expected_time"),
        [
            pytest.param("dash/test_dynamic_no_publish_time_timeline_with_start.mpd", "155994772214430", id="with-start"),
            pytest.param("dash/test_dynamic_no_publish_time_timeline_without_start.mpd", "4320000", id="without-start"),
        ],
    )
    def test_dynamic_no_publish_time_with_timeline(self, manifest: str, expected_time: str):
        with xml(manifest) as mpd_xml:
            mpd = MPD(mpd_xml, base_url="http://test/", url="http://test/manifest.mpd")

        segments = [
            (segment.uri, segment.num, segment.duration, segment.available_at, segment.init, segment.content)
            for segment in itertools.islice(mpd.periods[0].adaptationSets[0].representations[0].segments(), 100)
        ]
        assert segments == [
            (
                f"http://test/video_1920x1080_avc1-{expected_time}.m4s",
                9,
                6.0,
                datetime.datetime(1970, 1, 1, 0, 0, 0, tzinfo=UTC),
                False,
                True,
            ),
        ]

    def test_segment_list(self):
        with xml("dash/test_segment_list.mpd") as mpd_xml:
            mpd = MPD(mpd_xml, base_url="http://test/", url="http://test/manifest.mpd")

        segments = mpd.periods[0].adaptationSets[0].representations[0].segments()
        segment_urls = [(segment.uri, segment.available_at) for segment in itertools.islice(segments, 4)]
        # ignores period start time in static manifests
        expected_availability = datetime.datetime(2020, 1, 1, 0, 0, 0, tzinfo=UTC)

        assert segment_urls == [
            ("http://test/chunk_ctvideo_ridp0va0br4332748_cinit_mpd.m4s", expected_availability),
            ("http://test/chunk_ctvideo_ridp0va0br4332748_cn1_mpd.m4s", expected_availability),
            ("http://test/chunk_ctvideo_ridp0va0br4332748_cn2_mpd.m4s", expected_availability),
            ("http://test/chunk_ctvideo_ridp0va0br4332748_cn3_mpd.m4s", expected_availability),
        ]

    def test_dynamic_segment_list_continued(self, caplog: pytest.LogCaptureFixture):
        caplog.set_level("WARNING", "streamlink.stream.dash")

        # init manifest
        with xml("dash/test_dynamic_segment_list_p1.mpd") as mpd_xml:
            mpd = MPD(mpd_xml, base_url="http://test/", url="http://test/manifest.mpd")
        segments_iterator = mpd.periods[0].adaptationSets[0].representations[0].segments(init=True)

        assert [(segment.uri, segment.num) for segment in segments_iterator] == [
            ("http://test/init.m4s", -1),
            ("http://test/13.m4s", 13),
            ("http://test/14.m4s", 14),
            ("http://test/15.m4s", 15),
        ], "Queues the init segment and the correct number of segments from the live-edge"
        assert mpd.timelines["0", "0", "0"] == 16, "Remembers the next segment number"
        assert [(record.name, record.levelname, record.message) for record in caplog.records] == []

        # regular continuation
        with xml("dash/test_dynamic_segment_list_p2.mpd") as mpd_xml:
            mpd = MPD(mpd_xml, base_url="http://test/", url="http://test/manifest.mpd", timelines=mpd.timelines)
        segments_iterator = mpd.periods[0].adaptationSets[0].representations[0].segments(init=False)

        assert [(segment.uri, segment.num) for segment in segments_iterator] == [
            ("http://test/16.m4s", 16),
            ("http://test/17.m4s", 17),
            ("http://test/18.m4s", 18),
        ], "All segments from the remembered segment number were queued"
        assert mpd.timelines["0", "0", "0"] == 19, "Remembers the next segment number"
        assert [(record.name, record.levelname, record.message) for record in caplog.records] == []

        # regular continuation with a different offset
        with xml("dash/test_dynamic_segment_list_p3.mpd") as mpd_xml:
            mpd = MPD(mpd_xml, base_url="http://test/", url="http://test/manifest.mpd", timelines=mpd.timelines)
        segments_iterator = mpd.periods[0].adaptationSets[0].representations[0].segments(init=False)

        assert [(segment.uri, segment.num) for segment in segments_iterator] == [
            ("http://test/19.m4s", 19),
            ("http://test/20.m4s", 20),
            ("http://test/21.m4s", 21),
            ("http://test/22.m4s", 22),
            ("http://test/23.m4s", 23),
            ("http://test/24.m4s", 24),
        ], "All segments from the remembered segment number were queued"
        assert mpd.timelines["0", "0", "0"] == 25, "Remembers the next segment number"
        assert [(record.name, record.levelname, record.message) for record in caplog.records] == []

        # skipped multiple segments
        with xml("dash/test_dynamic_segment_list_p4.mpd") as mpd_xml:
            mpd = MPD(mpd_xml, base_url="http://test/", url="http://test/manifest.mpd", timelines=mpd.timelines)
        segments_iterator = mpd.periods[0].adaptationSets[0].representations[0].segments(init=False)

        assert [(segment.uri, segment.num) for segment in segments_iterator] == [
            ("http://test/30.m4s", 30),
            ("http://test/31.m4s", 31),
            ("http://test/32.m4s", 32),
            ("http://test/33.m4s", 33),
            ("http://test/34.m4s", 34),
            ("http://test/35.m4s", 35),
            ("http://test/36.m4s", 36),
            ("http://test/37.m4s", 37),
            ("http://test/38.m4s", 38),
            ("http://test/39.m4s", 39),
        ], "All segments from the remembered segment number were queued"
        assert mpd.timelines["0", "0", "0"] == 40, "Remembers the next segment number"
        assert [(record.name, record.levelname, record.message) for record in caplog.records] == [
            (
                "streamlink.stream.dash.manifest",
                "warning",
                "Skipped segments 25-29 after manifest reload. This is unsupported and will result in incoherent output data.",
            ),
        ]

        caplog.records.clear()

        # skipped single segment
        with xml("dash/test_dynamic_segment_list_p5.mpd") as mpd_xml:
            mpd = MPD(mpd_xml, base_url="http://test/", url="http://test/manifest.mpd", timelines=mpd.timelines)
        segments_iterator = mpd.periods[0].adaptationSets[0].representations[0].segments(init=False)

        assert [(segment.uri, segment.num) for segment in segments_iterator] == [
            ("http://test/41.m4s", 41),
            ("http://test/42.m4s", 42),
            ("http://test/43.m4s", 43),
            ("http://test/44.m4s", 44),
            ("http://test/45.m4s", 45),
            ("http://test/46.m4s", 46),
            ("http://test/47.m4s", 47),
            ("http://test/48.m4s", 48),
            ("http://test/49.m4s", 49),
            ("http://test/50.m4s", 50),
        ], "All segments from the remembered segment number were queued"
        assert mpd.timelines["0", "0", "0"] == 51, "Remembers the next segment number"
        assert [(record.name, record.levelname, record.message) for record in caplog.records] == [
            (
                "streamlink.stream.dash.manifest",
                "warning",
                "Skipped segment 40 after manifest reload. This is unsupported and will result in incoherent output data.",
            ),
        ]

    def test_dynamic_segment_list_no_duration(self):
        with xml("dash/test_dynamic_segment_list_no_duration.mpd") as mpd_xml:
            mpd = MPD(mpd_xml, base_url="http://test/", url="http://test/manifest.mpd")

        segments_iterator = mpd.periods[0].adaptationSets[0].representations[0].segments(init=True)
        assert [segment.uri for segment in segments_iterator] == [
            "http://test/init.m4s",
            "http://test/13.m4s",
            "http://test/14.m4s",
            "http://test/15.m4s",
        ]

    def test_dynamic_timeline_continued(self):
        with xml("dash/test_dynamic_timeline_continued_p1.mpd") as mpd_xml_p1:
            mpd_p1 = MPD(mpd_xml_p1, base_url="http://test/", url="http://test/manifest.mpd")
            iter_segment_p1 = mpd_p1.periods[0].adaptationSets[0].representations[0].segments()
            segments_p1 = [
                (segment.uri, segment.num, segment.duration, segment.available_at)
                for segment in itertools.islice(iter_segment_p1, 100)
            ]  # fmt: skip

        assert segments_p1 == [
            ("http://test/video/init.mp4", -1, 0.0, datetime.datetime(2018, 1, 1, 1, 0, 0, tzinfo=UTC)),
            ("http://test/video/1006000.mp4", 7, 1.0, datetime.datetime(2018, 1, 1, 12, 59, 56, tzinfo=UTC)),
            ("http://test/video/1007000.mp4", 8, 1.0, datetime.datetime(2018, 1, 1, 12, 59, 57, tzinfo=UTC)),
            ("http://test/video/1008000.mp4", 9, 1.0, datetime.datetime(2018, 1, 1, 12, 59, 58, tzinfo=UTC)),
            ("http://test/video/1009000.mp4", 10, 1.0, datetime.datetime(2018, 1, 1, 12, 59, 59, tzinfo=UTC)),
            ("http://test/video/1010000.mp4", 11, 1.0, datetime.datetime(2018, 1, 1, 13, 0, 0, tzinfo=UTC)),
        ]

        # continue with the next manifest
        with xml("dash/test_dynamic_timeline_continued_p2.mpd") as mpd_xml_p2:
            mpd_p2 = MPD(mpd_xml_p2, base_url=mpd_p1.base_url, url=mpd_p1.url, timelines=mpd_p1.timelines)
            iter_segment_p2 = mpd_p2.periods[0].adaptationSets[0].representations[0].segments(init=False)
            segments_p2 = [
                (segment.uri, segment.num, segment.duration, segment.available_at)
                for segment in itertools.islice(iter_segment_p2, 100)
            ]  # fmt: skip

        assert segments_p2 == [
            ("http://test/video/1011000.mp4", 7, 1.0, datetime.datetime(2018, 1, 1, 13, 0, 1, tzinfo=UTC)),
            ("http://test/video/1012000.mp4", 8, 1.0, datetime.datetime(2018, 1, 1, 13, 0, 2, tzinfo=UTC)),
            ("http://test/video/1013000.mp4", 9, 1.0, datetime.datetime(2018, 1, 1, 13, 0, 3, tzinfo=UTC)),
            ("http://test/video/1014000.mp4", 10, 1.0, datetime.datetime(2018, 1, 1, 13, 0, 4, tzinfo=UTC)),
            ("http://test/video/1015000.mp4", 11, 1.0, datetime.datetime(2018, 1, 1, 13, 0, 5, tzinfo=UTC)),
        ]

    def test_tsegment_t_is_none_1895(self):
        """
        Verify the fix for https://github.com/streamlink/streamlink/issues/1895
        """
        with xml("dash/test_8.mpd") as mpd_xml:
            mpd = MPD(mpd_xml, base_url="http://test.se/", url="http://test.se/manifest.mpd")

            segments = mpd.periods[0].adaptationSets[0].representations[0].segments()
            init_segment = next(segments)
            assert init_segment.uri == "http://test.se/video-2799000-0.mp4?z32=CENSORED_SESSION"

            video_segments = [x.uri for x in itertools.islice(segments, 3)]
            assert video_segments == [
                "http://test.se/video-time=0-2799000-0.m4s?z32=CENSORED_SESSION",
                "http://test.se/video-time=4000-2799000-0.m4s?z32=CENSORED_SESSION",
                "http://test.se/video-time=8000-2799000-0.m4s?z32=CENSORED_SESSION",
            ]

    def test_bitrate_rounded(self):
        def mock_rep(bandwidth):
            node = Mock(
                tag="Representation",
                attrib={
                    "id": "test",
                    "bandwidth": bandwidth,
                    "mimeType": "video/mp4",
                },
            )
            node.findall.return_value = []

            root = Mock()
            root.parent = None
            period = Mock()
            period.parent = root
            aset = Mock()
            aset.parent = period

            return Representation(node, root=root, parent=aset, period=period)

        assert mock_rep(1.2 * 1000.0).bandwidth_rounded == pytest.approx(1.2)
        assert mock_rep(45.6 * 1000.0).bandwidth_rounded == pytest.approx(46.0)
        assert mock_rep(134.0 * 1000.0).bandwidth_rounded == pytest.approx(130.0)
        assert mock_rep(1324.0 * 1000.0).bandwidth_rounded == pytest.approx(1300.0)

    def test_duplicated_resolutions(self):
        """
        Verify the fix for https://github.com/streamlink/streamlink/issues/3365
        """
        with xml("dash/test_10.mpd") as mpd_xml:
            mpd = MPD(mpd_xml, base_url="http://test.se/", url="http://test.se/manifest.mpd")

            representations_0 = mpd.periods[0].adaptationSets[0].representations[0]
            assert representations_0.height == 804
            assert representations_0.bandwidth == pytest.approx(10000.0)
            representations_1 = mpd.periods[0].adaptationSets[0].representations[1]
            assert representations_1.height == 804
            assert representations_1.bandwidth == pytest.approx(8000.0)

    def test_segments_static_periods_duration(self):
        """
        Verify the fix for https://github.com/streamlink/streamlink/issues/2873
        """
        with xml("dash/test_11_static.mpd") as mpd_xml:
            mpd = MPD(mpd_xml, base_url="http://test.se/", url="http://test.se/manifest.mpd")
            duration = mpd.periods[0].duration.total_seconds()
            assert duration == pytest.approx(204.32)

    def test_segments_byterange(self):
        with xml("dash/test_segments_byterange.mpd") as mpd_xml:
            mpd = MPD(mpd_xml, base_url="http://test/", url="http://test/manifest.mpd")

        segment_urls = [
            [(seg.uri, seg.init, seg.byterange) for seg in adaptationset.representations[0].segments()]
            for adaptationset in mpd.periods[0].adaptationSets
        ]  # fmt: skip

        assert segment_urls == [
            [
                ("http://test/video-frag.mp4", True, (36, 711)),
                ("http://test/video-frag.mp4", False, (747, 875371)),
                ("http://test/video-frag.mp4", False, (876118, 590796)),
                ("http://test/video-frag.mp4", False, (1466914, 487041)),
                ("http://test/video-frag.mp4", False, (1953955, 40698)),
            ],
            [
                ("http://test/audio-frag.mp4", True, (32, 592)),
                ("http://test/audio-frag.mp4", False, (624, 123576)),
                ("http://test/audio-frag.mp4", False, (124200, 126104)),
                ("http://test/audio-frag.mp4", False, (250304, 124062)),
                ("http://test/audio-frag.mp4", False, (374366, 471)),
            ],
        ]

    def test_baseurl_urljoin_no_trailing_slash(self):
        with xml("dash/test_baseurl_urljoin.mpd") as mpd_xml:
            mpd = MPD(mpd_xml, base_url="https://foo/bar", url="https://test/manifest.mpd")

        segment_urls = [
            [
                (period.id, adaptationset.id, segment.uri)
                for segment in itertools.islice(representation.segments(), 2)
            ]
            for period in mpd.periods
            for adaptationset in period.adaptationSets
            for representation in adaptationset.representations
        ]  # fmt: skip
        assert segment_urls == [
            [
                ("empty-baseurl", "absolute-segments", "https://foo/absolute/init_video_5000kbps.m4s"),
                ("empty-baseurl", "absolute-segments", "https://foo/absolute/media_video_5000kbps-1.m4s"),
            ],
            [
                ("empty-baseurl", "relative-segments", "https://foo/relative/init_video_5000kbps.m4s"),
                ("empty-baseurl", "relative-segments", "https://foo/relative/media_video_5000kbps-1.m4s"),
            ],
            [
                ("baseurl-with-scheme", "absolute-segments", "https://host/absolute/init_video_5000kbps.m4s"),
                ("baseurl-with-scheme", "absolute-segments", "https://host/absolute/media_video_5000kbps-1.m4s"),
            ],
            [
                ("baseurl-with-scheme", "relative-segments", "https://host/path/relative/init_video_5000kbps.m4s"),
                ("baseurl-with-scheme", "relative-segments", "https://host/path/relative/media_video_5000kbps-1.m4s"),
            ],
            [
                ("absolute-baseurl", "absolute-segments", "https://foo/absolute/init_video_5000kbps.m4s"),
                ("absolute-baseurl", "absolute-segments", "https://foo/absolute/media_video_5000kbps-1.m4s"),
            ],
            [
                ("absolute-baseurl", "relative-segments", "https://foo/path/relative/init_video_5000kbps.m4s"),
                ("absolute-baseurl", "relative-segments", "https://foo/path/relative/media_video_5000kbps-1.m4s"),
            ],
            [
                ("relative-baseurl", "absolute-segments", "https://foo/absolute/init_video_5000kbps.m4s"),
                ("relative-baseurl", "absolute-segments", "https://foo/absolute/media_video_5000kbps-1.m4s"),
            ],
            [
                ("relative-baseurl", "relative-segments", "https://foo/path/relative/init_video_5000kbps.m4s"),
                ("relative-baseurl", "relative-segments", "https://foo/path/relative/media_video_5000kbps-1.m4s"),
            ],
        ]

    def test_baseurl_urljoin_with_trailing_slash(self):
        with xml("dash/test_baseurl_urljoin.mpd") as mpd_xml:
            mpd = MPD(mpd_xml, base_url="https://foo/bar/", url="https://test/manifest.mpd")

        segment_urls = [
            [
                (period.id, adaptationset.id, segment.uri)
                for segment in itertools.islice(representation.segments(), 2)
            ]
            for period in mpd.periods
            for adaptationset in period.adaptationSets
            for representation in adaptationset.representations
        ]  # fmt: skip
        assert segment_urls == [
            [
                ("empty-baseurl", "absolute-segments", "https://foo/absolute/init_video_5000kbps.m4s"),
                ("empty-baseurl", "absolute-segments", "https://foo/absolute/media_video_5000kbps-1.m4s"),
            ],
            [
                ("empty-baseurl", "relative-segments", "https://foo/bar/relative/init_video_5000kbps.m4s"),
                ("empty-baseurl", "relative-segments", "https://foo/bar/relative/media_video_5000kbps-1.m4s"),
            ],
            [
                ("baseurl-with-scheme", "absolute-segments", "https://host/absolute/init_video_5000kbps.m4s"),
                ("baseurl-with-scheme", "absolute-segments", "https://host/absolute/media_video_5000kbps-1.m4s"),
            ],
            [
                ("baseurl-with-scheme", "relative-segments", "https://host/path/relative/init_video_5000kbps.m4s"),
                ("baseurl-with-scheme", "relative-segments", "https://host/path/relative/media_video_5000kbps-1.m4s"),
            ],
            [
                ("absolute-baseurl", "absolute-segments", "https://foo/absolute/init_video_5000kbps.m4s"),
                ("absolute-baseurl", "absolute-segments", "https://foo/absolute/media_video_5000kbps-1.m4s"),
            ],
            [
                ("absolute-baseurl", "relative-segments", "https://foo/path/relative/init_video_5000kbps.m4s"),
                ("absolute-baseurl", "relative-segments", "https://foo/path/relative/media_video_5000kbps-1.m4s"),
            ],
            [
                ("relative-baseurl", "absolute-segments", "https://foo/absolute/init_video_5000kbps.m4s"),
                ("relative-baseurl", "absolute-segments", "https://foo/absolute/media_video_5000kbps-1.m4s"),
            ],
            [
                ("relative-baseurl", "relative-segments", "https://foo/bar/path/relative/init_video_5000kbps.m4s"),
                ("relative-baseurl", "relative-segments", "https://foo/bar/path/relative/media_video_5000kbps-1.m4s"),
            ],
        ]

    def test_baseurl_urljoin_empty(self):
        with xml("dash/test_baseurl_urljoin.mpd") as mpd_xml:
            mpd = MPD(mpd_xml, base_url="", url="https://test/manifest.mpd")

        segment_urls = [
            [
                (period.id, adaptationset.id, segment.uri)
                for segment in itertools.islice(representation.segments(), 2)
            ]
            for period in mpd.periods
            for adaptationset in period.adaptationSets
            for representation in adaptationset.representations
        ]  # fmt: skip
        assert segment_urls == [
            [
                ("empty-baseurl", "absolute-segments", "/absolute/init_video_5000kbps.m4s"),
                ("empty-baseurl", "absolute-segments", "/absolute/media_video_5000kbps-1.m4s"),
            ],
            [
                ("empty-baseurl", "relative-segments", "relative/init_video_5000kbps.m4s"),
                ("empty-baseurl", "relative-segments", "relative/media_video_5000kbps-1.m4s"),
            ],
            [
                ("baseurl-with-scheme", "absolute-segments", "https://host/absolute/init_video_5000kbps.m4s"),
                ("baseurl-with-scheme", "absolute-segments", "https://host/absolute/media_video_5000kbps-1.m4s"),
            ],
            [
                ("baseurl-with-scheme", "relative-segments", "https://host/path/relative/init_video_5000kbps.m4s"),
                ("baseurl-with-scheme", "relative-segments", "https://host/path/relative/media_video_5000kbps-1.m4s"),
            ],
            [
                ("absolute-baseurl", "absolute-segments", "/absolute/init_video_5000kbps.m4s"),
                ("absolute-baseurl", "absolute-segments", "/absolute/media_video_5000kbps-1.m4s"),
            ],
            [
                ("absolute-baseurl", "relative-segments", "/path/relative/init_video_5000kbps.m4s"),
                ("absolute-baseurl", "relative-segments", "/path/relative/media_video_5000kbps-1.m4s"),
            ],
            [
                ("relative-baseurl", "absolute-segments", "/absolute/init_video_5000kbps.m4s"),
                ("relative-baseurl", "absolute-segments", "/absolute/media_video_5000kbps-1.m4s"),
            ],
            [
                ("relative-baseurl", "relative-segments", "path/relative/init_video_5000kbps.m4s"),
                ("relative-baseurl", "relative-segments", "path/relative/media_video_5000kbps-1.m4s"),
            ],
        ]

    def test_baseurl_nested(self):
        with xml("dash/test_baseurl_nested.mpd") as mpd_xml:
            mpd = MPD(mpd_xml, base_url="https://foo/", url="https://test/manifest.mpd")

        segment_urls = [
            [(segment.uri, segment.available_at) for segment in itertools.islice(representation.segments(), 2)]
            for adaptationset in mpd.periods[0].adaptationSets
            for representation in adaptationset.representations
        ]
        # ignores period start time in static manifests
        expected_availability = datetime.datetime(2020, 1, 1, 0, 0, 0, tzinfo=UTC)

        assert segment_urls == [
            [
                ("https://hostname/period/init_video_5000kbps.m4s", expected_availability),
                ("https://hostname/period/media_video_5000kbps-1.m4s", expected_availability),
            ],
            [
                ("https://hostname/period/representation/init_video_9000kbps.m4s", expected_availability),
                ("https://hostname/period/representation/media_video_9000kbps-1.m4s", expected_availability),
            ],
            [
                ("https://hostname/period/adaptationset/init_audio_128kbps.m4s", expected_availability),
                ("https://hostname/period/adaptationset/media_audio_128kbps-1.m4s", expected_availability),
            ],
            [
                ("https://hostname/period/adaptationset/representation/init_audio_256kbps.m4s", expected_availability),
                ("https://hostname/period/adaptationset/representation/media_audio_256kbps-1.m4s", expected_availability),
            ],
            [
                ("https://other/init_audio_320kbps.m4s", expected_availability),
                ("https://other/media_audio_320kbps-1.m4s", expected_availability),
            ],
        ]

    def test_timeline_ids(self):
        with xml("dash/test_timeline_ids.mpd") as mpd_xml, freeze_time("2000-01-01T00:00:00Z"):
            mpd = MPD(mpd_xml, base_url="http://test/", url="http://test/manifest.mpd")
            segment_urls = [
                [segment.uri for segment in itertools.islice(representation.segments(), 3)]
                for adaptationset in mpd.periods[0].adaptationSets
                for representation in adaptationset.representations
            ]
        assert segment_urls == [
            [
                "http://test/audio1/init.mp4",
                "http://test/audio1/t0.m4s",
                "http://test/audio1/t1.m4s",
            ],
            [
                "http://test/audio2/init.mp4",
                "http://test/audio2/t0.m4s",
                "http://test/audio2/t1.m4s",
            ],
            [
                "http://test/video1/init.mp4",
                "http://test/video1/t0.m4s",
                "http://test/video1/t1.m4s",
            ],
            [
                "http://test/video2/init.mp4",
                "http://test/video2/t0.m4s",
                "http://test/video2/t1.m4s",
            ],
        ]
        assert list(mpd.timelines.keys()) == [
            ("period-0", "0", "audio1"),
            ("period-0", "0", "audio2"),
            ("period-0", None, "video1"),
            ("period-0", None, "video2"),
        ]

    def test_get_representation(self):
        with xml("dash/test_timeline_ids.mpd") as mpd_xml:
            mpd = MPD(mpd_xml, base_url="http://test/", url="http://test/manifest.mpd")

        assert mpd.get_representation((None, None, "unknown")) is None
        assert mpd.get_representation((None, None, "audio1")) is None
        assert mpd.get_representation((None, "0", "audio1")) is None
        assert mpd.get_representation(("period-0", None, "audio1")) is None

        assert getattr(mpd.get_representation(("period-0", "0", "audio1")), "mimeType", None) == "audio/mp4"
        assert getattr(mpd.get_representation(("period-0", "0", "audio2")), "mimeType", None) == "audio/mp4"
        assert getattr(mpd.get_representation(("period-0", None, "video1")), "mimeType", None) == "video/mp4"
        assert getattr(mpd.get_representation(("period-0", None, "video2")), "mimeType", None) == "video/mp4"
