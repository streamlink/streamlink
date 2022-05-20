import datetime
import itertools
import unittest
from operator import attrgetter
from unittest.mock import Mock

from freezegun import freeze_time
from freezegun.api import FakeDatetime  # type: ignore[attr-defined]

from streamlink.stream.dash_manifest import MPD, MPDParsers, MPDParsingError, Representation, utc
from tests.resources import xml


class TestMPDParsers(unittest.TestCase):
    def test_utc(self):
        self.assertEqual(utc.tzname(None), "UTC")
        self.assertEqual(utc.dst(None), datetime.timedelta(0))
        self.assertEqual(utc.utcoffset(None), datetime.timedelta(0))

    def test_bool_str(self):
        self.assertEqual(MPDParsers.bool_str("true"), True)
        self.assertEqual(MPDParsers.bool_str("TRUE"), True)
        self.assertEqual(MPDParsers.bool_str("True"), True)

        self.assertEqual(MPDParsers.bool_str("0"), False)
        self.assertEqual(MPDParsers.bool_str("False"), False)
        self.assertEqual(MPDParsers.bool_str("false"), False)
        self.assertEqual(MPDParsers.bool_str("FALSE"), False)

    def test_type(self):
        self.assertEqual(MPDParsers.type("dynamic"), "dynamic")
        self.assertEqual(MPDParsers.type("static"), "static")
        with self.assertRaises(MPDParsingError):
            MPDParsers.type("other")

    def test_duration(self):
        self.assertEqual(MPDParsers.duration("PT1S"), datetime.timedelta(0, 1))

    def test_datetime(self):
        self.assertEqual(MPDParsers.datetime("2018-01-01T00:00:00Z"),
                         datetime.datetime(2018, 1, 1, 0, 0, 0, tzinfo=utc))

    def test_segment_template(self):
        self.assertEqual(MPDParsers.segment_template("$Time$-$Number$-$Other$")(Time=1, Number=2, Other=3),
                         "1-2-3")
        self.assertEqual(MPDParsers.segment_template("$Number%05d$")(Number=123),
                         "00123")
        self.assertEqual(MPDParsers.segment_template("$Time%0.02f$")(Time=100.234),
                         "100.23")

    def test_frame_rate(self):
        self.assertAlmostEqual(MPDParsers.frame_rate("1/25"),
                               1 / 25.0)
        self.assertAlmostEqual(MPDParsers.frame_rate("0.2"),
                               0.2)

    def test_timedelta(self):
        self.assertEqual(MPDParsers.timedelta(1)(100),
                         datetime.timedelta(0, 100.0))
        self.assertEqual(MPDParsers.timedelta(10)(100),
                         datetime.timedelta(0, 10.0))

    def test_range(self):
        self.assertEqual(MPDParsers.range("100-"), (100, None))
        self.assertEqual(MPDParsers.range("100-199"), (100, 100))
        self.assertRaises(MPDParsingError, MPDParsers.range, "100")


class TestMPDParser(unittest.TestCase):
    maxDiff = None

    def test_segments_number_time(self):
        with xml("dash/test_1.mpd") as mpd_xml:
            mpd = MPD(mpd_xml, base_url="http://test.se/", url="http://test.se/manifest.mpd")

            segments = mpd.periods[0].adaptationSets[0].representations[0].segments()
            init_segment = next(segments)
            self.assertEqual(init_segment.url, "http://test.se/tracks-v3/init-1526842800.g_m4v")

            video_segments = list(map(attrgetter("url"), (itertools.islice(segments, 5))))
            # suggested delay is 11 seconds, each segment is 5 seconds long - so there should be 3
            self.assertSequenceEqual(video_segments,
                                     ['http://test.se/tracks-v3/dvr-1526842800-698.g_m4v?t=3403000',
                                      'http://test.se/tracks-v3/dvr-1526842800-699.g_m4v?t=3408000',
                                      'http://test.se/tracks-v3/dvr-1526842800-700.g_m4v?t=3413000'])

    def test_segments_static_number(self):
        with xml("dash/test_2.mpd") as mpd_xml:
            mpd = MPD(mpd_xml, base_url="http://test.se/", url="http://test.se/manifest.mpd")

            segments = mpd.periods[0].adaptationSets[3].representations[0].segments()
            init_segment = next(segments)
            self.assertEqual(init_segment.url, "http://test.se/video/250kbit/init.mp4")

            video_segments = list(map(attrgetter("url"), (itertools.islice(segments, 100000))))
            self.assertEqual(len(video_segments), 444)
            self.assertSequenceEqual(video_segments[:5],
                                     ['http://test.se/video/250kbit/segment_1.m4s',
                                      'http://test.se/video/250kbit/segment_2.m4s',
                                      'http://test.se/video/250kbit/segment_3.m4s',
                                      'http://test.se/video/250kbit/segment_4.m4s',
                                      'http://test.se/video/250kbit/segment_5.m4s'])

    def test_segments_dynamic_time(self):
        with xml("dash/test_3.mpd") as mpd_xml:
            mpd = MPD(mpd_xml, base_url="http://test.se/", url="http://test.se/manifest.mpd")

            segments = mpd.periods[0].adaptationSets[0].representations[0].segments()
            init_segment = next(segments)
            self.assertEqual(init_segment.url, "http://test.se/video-2800000-0.mp4?z32=")

            video_segments = list(map(attrgetter("url"), (itertools.islice(segments, 3))))
            # default suggested delay is 3 seconds, each segment is 4 seconds long - so there should be 1 segment
            self.assertSequenceEqual(video_segments,
                                     ['http://test.se/video-time=1525450872000-2800000-0.m4s?z32='])

    def test_segments_dynamic_number(self):
        with freeze_time(FakeDatetime(2018, 5, 22, 13, 37, 0, tzinfo=utc)):
            with xml("dash/test_4.mpd") as mpd_xml:
                mpd = MPD(mpd_xml, base_url="http://test.se/", url="http://test.se/manifest.mpd")

                segments = mpd.periods[0].adaptationSets[0].representations[0].segments()
                init_segment = next(segments)
                self.assertEqual(init_segment.url, "http://test.se/hd-5-init.mp4")

                video_segments = []
                for _ in range(3):
                    seg = next(segments)
                    video_segments.append((seg.url,
                                           seg.available_at))

                self.assertSequenceEqual(video_segments,
                                         [('http://test.se/hd-5_000311235.mp4',
                                           datetime.datetime(2018, 5, 22, 13, 37, 0, tzinfo=utc)),
                                          ('http://test.se/hd-5_000311236.mp4',
                                           datetime.datetime(2018, 5, 22, 13, 37, 5, tzinfo=utc)),
                                          ('http://test.se/hd-5_000311237.mp4',
                                           datetime.datetime(2018, 5, 22, 13, 37, 10, tzinfo=utc))
                                          ])

    def test_segments_static_no_publish_time(self):
        with xml("dash/test_5.mpd") as mpd_xml:
            mpd = MPD(mpd_xml, base_url="http://test.se/", url="http://test.se/manifest.mpd")

            segments = mpd.periods[0].adaptationSets[1].representations[0].segments()
            init_segment = next(segments)
            self.assertEqual(init_segment.url, "http://test.se/dash/150633-video_eng=194000.dash")

            video_segments = [x.url for x in itertools.islice(segments, 3)]
            self.assertSequenceEqual(video_segments,
                                     ['http://test.se/dash/150633-video_eng=194000-0.dash',
                                      'http://test.se/dash/150633-video_eng=194000-2000.dash',
                                      'http://test.se/dash/150633-video_eng=194000-4000.dash',
                                      ])

    def test_segments_list(self):
        with xml("dash/test_7.mpd") as mpd_xml:
            mpd = MPD(mpd_xml, base_url="http://test.se/", url="http://test.se/manifest.mpd")

            segments = mpd.periods[0].adaptationSets[0].representations[0].segments()
            init_segment = next(segments)
            self.assertEqual(init_segment.url, "http://test.se/chunk_ctvideo_ridp0va0br4332748_cinit_mpd.m4s")

            video_segments = [x.url for x in itertools.islice(segments, 3)]
            self.assertSequenceEqual(video_segments,
                                     ['http://test.se/chunk_ctvideo_ridp0va0br4332748_cn1_mpd.m4s',
                                      'http://test.se/chunk_ctvideo_ridp0va0br4332748_cn2_mpd.m4s',
                                      'http://test.se/chunk_ctvideo_ridp0va0br4332748_cn3_mpd.m4s',
                                      ])

    def test_segments_dynamic_timeline_continue(self):
        with xml("dash/test_6_p1.mpd") as mpd_xml_p1:
            with xml("dash/test_6_p2.mpd") as mpd_xml_p2:
                mpd_p1 = MPD(mpd_xml_p1, base_url="http://test.se/", url="http://test.se/manifest.mpd")

                segments_p1 = mpd_p1.periods[0].adaptationSets[0].representations[0].segments()
                init_segment = next(segments_p1)
                self.assertEqual(init_segment.url, "http://test.se/video/init.mp4")

                video_segments_p1 = [x.url for x in itertools.islice(segments_p1, 100)]
                self.assertSequenceEqual(video_segments_p1,
                                         ['http://test.se/video/1006000.mp4',
                                          'http://test.se/video/1007000.mp4',
                                          'http://test.se/video/1008000.mp4',
                                          'http://test.se/video/1009000.mp4',
                                          'http://test.se/video/1010000.mp4'])

                # Continue in the next manifest
                mpd_p2 = MPD(mpd_xml_p2,
                             base_url=mpd_p1.base_url,
                             url=mpd_p1.url,
                             timelines=mpd_p1.timelines)

                segments_p2 = mpd_p2.periods[0].adaptationSets[0].representations[0].segments(init=False)
                video_segments_p2 = [x.url for x in itertools.islice(segments_p2, 100)]
                self.assertSequenceEqual(video_segments_p2,
                                         ['http://test.se/video/1011000.mp4',
                                          'http://test.se/video/1012000.mp4',
                                          'http://test.se/video/1013000.mp4',
                                          'http://test.se/video/1014000.mp4',
                                          'http://test.se/video/1015000.mp4'])

    def test_tsegment_t_is_none_1895(self):
        """
            Verify the fix for https://github.com/streamlink/streamlink/issues/1895
        """
        with xml("dash/test_8.mpd") as mpd_xml:
            mpd = MPD(mpd_xml, base_url="http://test.se/", url="http://test.se/manifest.mpd")

            segments = mpd.periods[0].adaptationSets[0].representations[0].segments()
            init_segment = next(segments)
            self.assertEqual(init_segment.url, "http://test.se/video-2799000-0.mp4?z32=CENSORED_SESSION")

            video_segments = [x.url for x in itertools.islice(segments, 3)]
            self.assertSequenceEqual(video_segments,
                                     ['http://test.se/video-time=0-2799000-0.m4s?z32=CENSORED_SESSION',
                                      'http://test.se/video-time=4000-2799000-0.m4s?z32=CENSORED_SESSION',
                                      'http://test.se/video-time=8000-2799000-0.m4s?z32=CENSORED_SESSION',
                                      ])

    def test_bitrate_rounded(self):
        def mock_rep(bandwidth):
            node = Mock(
                tag="Representation",
                attrib={
                    "id": "test",
                    "bandwidth": bandwidth,
                    "mimeType": "video/mp4"
                }
            )
            node.findall.return_value = []
            return Representation(node)

        self.assertEqual(mock_rep(1.2 * 1000.0).bandwidth_rounded, 1.2)
        self.assertEqual(mock_rep(45.6 * 1000.0).bandwidth_rounded, 46.0)
        self.assertEqual(mock_rep(134.0 * 1000.0).bandwidth_rounded, 130.0)
        self.assertEqual(mock_rep(1324.0 * 1000.0).bandwidth_rounded, 1300.0)

    def test_duplicated_resolutions(self):
        """
            Verify the fix for https://github.com/streamlink/streamlink/issues/3365
        """
        with xml("dash/test_10.mpd") as mpd_xml:
            mpd = MPD(mpd_xml, base_url="http://test.se/", url="http://test.se/manifest.mpd")

            representations_0 = mpd.periods[0].adaptationSets[0].representations[0]
            self.assertEqual(representations_0.height, 804)
            self.assertEqual(representations_0.bandwidth, 10000.0)
            representations_1 = mpd.periods[0].adaptationSets[0].representations[1]
            self.assertEqual(representations_1.height, 804)
            self.assertEqual(representations_1.bandwidth, 8000.0)

    def test_segments_static_periods_duration(self):
        """
            Verify the fix for https://github.com/streamlink/streamlink/issues/2873
        """
        with xml("dash/test_11_static.mpd") as mpd_xml:
            mpd = MPD(mpd_xml, base_url="http://test.se/", url="http://test.se/manifest.mpd")
            duration = mpd.periods[0].duration.total_seconds()
            self.assertEqual(duration, 204.32)
