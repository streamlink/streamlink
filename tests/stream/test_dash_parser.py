import datetime
import itertools
import unittest
from operator import attrgetter
from unittest.mock import Mock

import pytest
from freezegun import freeze_time

from streamlink.stream.dash_manifest import MPD, MPDParsers, MPDParsingError, Representation
from tests.resources import xml


UTC = datetime.timezone.utc


class TestMPDParsers(unittest.TestCase):
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
            MPDParsers.type("other")

    def test_duration(self):
        assert MPDParsers.duration("PT1S") == datetime.timedelta(0, 1)

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


class TestMPDParser(unittest.TestCase):
    maxDiff = None

    def test_segments_number_time(self):
        with xml("dash/test_1.mpd") as mpd_xml:
            mpd = MPD(mpd_xml, base_url="http://test.se/", url="http://test.se/manifest.mpd")

            segments = mpd.periods[0].adaptationSets[0].representations[0].segments()
            init_segment = next(segments)
            assert init_segment.url == "http://test.se/tracks-v3/init-1526842800.g_m4v"

            video_segments = list(map(attrgetter("url"), (itertools.islice(segments, 5))))
            # suggested delay is 11 seconds, each segment is 5 seconds long - so there should be 3
            assert video_segments == [
                "http://test.se/tracks-v3/dvr-1526842800-698.g_m4v?t=3403000",
                "http://test.se/tracks-v3/dvr-1526842800-699.g_m4v?t=3408000",
                "http://test.se/tracks-v3/dvr-1526842800-700.g_m4v?t=3413000",
            ]

    def test_segments_static_number(self):
        with xml("dash/test_2.mpd") as mpd_xml:
            mpd = MPD(mpd_xml, base_url="http://test.se/", url="http://test.se/manifest.mpd")

            segments = mpd.periods[0].adaptationSets[3].representations[0].segments()
            init_segment = next(segments)
            assert init_segment.url == "http://test.se/video/250kbit/init.mp4"

            video_segments = list(map(attrgetter("url"), (itertools.islice(segments, 100000))))
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
            assert init_segment.url == "http://test.se/video-2800000-0.mp4?z32="

            video_segments = list(map(attrgetter("url"), (itertools.islice(segments, 3))))
            # default suggested delay is 3 seconds, each segment is 4 seconds long - so there should be 1 segment
            assert video_segments == [
                "http://test.se/video-time=1525450872000-2800000-0.m4s?z32=",
            ]

    def test_segments_dynamic_number(self):
        # access manifest one hour after its availabilityStartTime
        with xml("dash/test_segments_dynamic_number.mpd") as mpd_xml, \
             freeze_time("2000-01-01T01:00:00Z"):
            mpd = MPD(mpd_xml, base_url="http://test/", url="http://test/manifest.mpd")
            stream_urls = [
                (segment.url, segment.available_at)
                for segment in itertools.islice(mpd.periods[0].adaptationSets[0].representations[0].segments(), 4)
            ]

        assert stream_urls == [
            (
                "http://test/hd-5-init.mp4",
                datetime.datetime(2000, 1, 1, 0, 1, 30, tzinfo=UTC),
            ),
            (
                "http://test/hd-5_000000794.mp4",
                datetime.datetime(2000, 1, 1, 0, 59, 15, tzinfo=UTC),
            ),
            (
                "http://test/hd-5_000000795.mp4",
                datetime.datetime(2000, 1, 1, 0, 59, 20, tzinfo=UTC),
            ),
            (
                "http://test/hd-5_000000796.mp4",
                datetime.datetime(2000, 1, 1, 0, 59, 25, tzinfo=UTC),
            ),
        ]

    def test_static_no_publish_time(self):
        with xml("dash/test_static_no_publish_time.mpd") as mpd_xml:
            mpd = MPD(mpd_xml, base_url="http://test/", url="http://test/manifest.mpd")

        segments = mpd.periods[0].adaptationSets[1].representations[0].segments()
        segment_urls = [(segment.url, segment.available_at) for segment in itertools.islice(segments, 4)]
        # ignores period start time in static manifests
        expected_availability = datetime.datetime(2020, 1, 1, 0, 0, 0, tzinfo=UTC)

        assert segment_urls == [
            ("http://test/dash/150633-video_eng=194000.dash", expected_availability),
            ("http://test/dash/150633-video_eng=194000-0.dash", expected_availability),
            ("http://test/dash/150633-video_eng=194000-2000.dash", expected_availability),
            ("http://test/dash/150633-video_eng=194000-4000.dash", expected_availability),
        ]

    def test_segment_list(self):
        with xml("dash/test_segment_list.mpd") as mpd_xml:
            mpd = MPD(mpd_xml, base_url="http://test/", url="http://test/manifest.mpd")

        segments = mpd.periods[0].adaptationSets[0].representations[0].segments()
        segment_urls = [(segment.url, segment.available_at) for segment in itertools.islice(segments, 4)]
        # ignores period start time in static manifests
        expected_availability = datetime.datetime(2020, 1, 1, 0, 0, 0, tzinfo=UTC)

        assert segment_urls == [
            ("http://test/chunk_ctvideo_ridp0va0br4332748_cinit_mpd.m4s", expected_availability),
            ("http://test/chunk_ctvideo_ridp0va0br4332748_cn1_mpd.m4s", expected_availability),
            ("http://test/chunk_ctvideo_ridp0va0br4332748_cn2_mpd.m4s", expected_availability),
            ("http://test/chunk_ctvideo_ridp0va0br4332748_cn3_mpd.m4s", expected_availability),
        ]

    def test_segments_dynamic_timeline_continue(self):
        with xml("dash/test_6_p1.mpd") as mpd_xml_p1:
            with xml("dash/test_6_p2.mpd") as mpd_xml_p2:
                mpd_p1 = MPD(mpd_xml_p1, base_url="http://test.se/", url="http://test.se/manifest.mpd")

                segments_p1 = mpd_p1.periods[0].adaptationSets[0].representations[0].segments()
                init_segment = next(segments_p1)
                assert init_segment.url == "http://test.se/video/init.mp4"

                video_segments_p1 = [x.url for x in itertools.islice(segments_p1, 100)]
                assert video_segments_p1 == [
                    "http://test.se/video/1006000.mp4",
                    "http://test.se/video/1007000.mp4",
                    "http://test.se/video/1008000.mp4",
                    "http://test.se/video/1009000.mp4",
                    "http://test.se/video/1010000.mp4",
                ]

                # Continue in the next manifest
                mpd_p2 = MPD(mpd_xml_p2,
                             base_url=mpd_p1.base_url,
                             url=mpd_p1.url,
                             timelines=mpd_p1.timelines)

                segments_p2 = mpd_p2.periods[0].adaptationSets[0].representations[0].segments(init=False)
                video_segments_p2 = [x.url for x in itertools.islice(segments_p2, 100)]
                assert video_segments_p2 == [
                    "http://test.se/video/1011000.mp4",
                    "http://test.se/video/1012000.mp4",
                    "http://test.se/video/1013000.mp4",
                    "http://test.se/video/1014000.mp4",
                    "http://test.se/video/1015000.mp4",
                ]

    def test_tsegment_t_is_none_1895(self):
        """
            Verify the fix for https://github.com/streamlink/streamlink/issues/1895
        """
        with xml("dash/test_8.mpd") as mpd_xml:
            mpd = MPD(mpd_xml, base_url="http://test.se/", url="http://test.se/manifest.mpd")

            segments = mpd.periods[0].adaptationSets[0].representations[0].segments()
            init_segment = next(segments)
            assert init_segment.url == "http://test.se/video-2799000-0.mp4?z32=CENSORED_SESSION"

            video_segments = [x.url for x in itertools.islice(segments, 3)]
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
            return Representation(node, parent=Mock())

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
            [
                (seg.url, seg.init, seg.byterange)
                for seg in adaptationset.representations[0].segments()
            ]
            for adaptationset in mpd.periods[0].adaptationSets
        ]

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

    def test_nested_baseurls(self):
        with xml("dash/test_nested_baseurls.mpd") as mpd_xml:
            mpd = MPD(mpd_xml, base_url="https://foo/", url="https://test/manifest.mpd")

        segment_urls = [
            [(segment.url, segment.available_at) for segment in itertools.islice(representation.segments(), 2)]
            for adaptationset in mpd.periods[0].adaptationSets for representation in adaptationset.representations
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
        with xml("dash/test_timeline_ids.mpd") as mpd_xml, \
             freeze_time("2000-01-01T00:00:00Z"):
            mpd = MPD(mpd_xml, base_url="http://test/", url="http://test/manifest.mpd")
            segment_urls = [
                [
                    segment.url
                    for segment in itertools.islice(representation.segments(), 3)
                ]
                for adaptationset in mpd.periods[0].adaptationSets for representation in adaptationset.representations
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
