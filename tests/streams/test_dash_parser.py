from __future__ import unicode_literals

import datetime
from freezegun import freeze_time

import itertools
from operator import attrgetter

from freezegun.api import FakeDatetime

from streamlink.stream.dash_manifest import MPD, MPDParsers, MPDParsingError, utc, datetime_to_seconds
from tests import unittest
from tests.resources import xml


class TestMPDParsers(unittest.TestCase):
    def test_utc(self):
        self.assertIn(utc.tzname(None), ("UTC", "UTC+00:00"))  # depends on the implementation
        self.assertIn(utc.dst(None), (None, datetime.timedelta(0)))  # depends on the implementation
        self.assertEqual(utc.utcoffset(None), datetime.timedelta(0))

    def test_bool_str(self):
        self.assertEquals(MPDParsers.bool_str("true"), True)
        self.assertEquals(MPDParsers.bool_str("TRUE"), True)
        self.assertEquals(MPDParsers.bool_str("True"), True)

        self.assertEquals(MPDParsers.bool_str("0"), False)
        self.assertEquals(MPDParsers.bool_str("False"), False)
        self.assertEquals(MPDParsers.bool_str("false"), False)
        self.assertEquals(MPDParsers.bool_str("FALSE"), False)

    def test_type(self):
        self.assertEquals(MPDParsers.type("dynamic"), "dynamic")
        self.assertEquals(MPDParsers.type("static"), "static")
        with self.assertRaises(MPDParsingError):
            MPDParsers.type("other")

    def test_duration(self):
        self.assertEquals(MPDParsers.duration("PT1S"), datetime.timedelta(0, 1))

    def test_datetime(self):
        self.assertEquals(MPDParsers.datetime("2018-01-01T00:00:00Z"),
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


class TestMPDParser(unittest.TestCase):
    def test_segments_number_time(self):
        with xml("dash/test_1.mpd") as mpd_xml:
            mpd = MPD(mpd_xml, base_url="http://test.se/", url="http://test.se/manifest.mpd")

            segments = mpd.periods[0].adaptationSets[0].representations[0].segments()
            init_segment = next(segments)
            self.assertEqual(init_segment.url, "http://test.se/tracks-v3/init-1526842800.g_m4v")

            video_segments = list(map(attrgetter("url"), (itertools.islice(segments, 5))))
            self.assertSequenceEqual(video_segments,
                                     ['http://test.se/tracks-v3/dvr-1526842800-695.g_m4v?t=3388000',
                                      'http://test.se/tracks-v3/dvr-1526842800-696.g_m4v?t=3393000',
                                      'http://test.se/tracks-v3/dvr-1526842800-697.g_m4v?t=3398000',
                                      'http://test.se/tracks-v3/dvr-1526842800-698.g_m4v?t=3403000',
                                      'http://test.se/tracks-v3/dvr-1526842800-699.g_m4v?t=3408000'])

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
            self.assertSequenceEqual(video_segments[:3],
                                     ['http://test.se/video-time=1525450860000-2800000-0.m4s?z32=',
                                      'http://test.se/video-time=1525450864000-2800000-0.m4s?z32=',
                                      'http://test.se/video-time=1525450868000-2800000-0.m4s?z32='])

    def test_segments_dynamic_number(self):
        with freeze_time(FakeDatetime(2018, 5, 22, 13, 37, 0, tzinfo=utc)) as frozen_datetime:
            with xml("dash/test_4.mpd") as mpd_xml:
                mpd = MPD(mpd_xml, base_url="http://test.se/", url="http://test.se/manifest.mpd")

                segments = mpd.periods[0].adaptationSets[0].representations[0].segments()
                init_segment = next(segments)
                self.assertEqual(init_segment.url, "http://test.se/hd-5-init.mp4")

                video_segments = []
                for _ in range(3):
                    seg = next(segments)
                    video_segments.append((seg.url,
                                           seg.available_at,
                                           datetime.datetime.now(tz=utc)))
                    frozen_datetime.tick(5)

                self.assertSequenceEqual(video_segments,
                                         [('http://test.se/hd-5_000311235.mp4',
                                           datetime.datetime(2018, 5, 22, 13, 36, 20, tzinfo=utc),
                                           datetime.datetime(2018, 5, 22, 13, 37, 0, tzinfo=utc)),
                                          ('http://test.se/hd-5_000311236.mp4',
                                           datetime.datetime(2018, 5, 22, 13, 36, 25, tzinfo=utc),
                                           datetime.datetime(2018, 5, 22, 13, 37, 5, tzinfo=utc)),
                                          ('http://test.se/hd-5_000311237.mp4',
                                           datetime.datetime(2018, 5, 22, 13, 36, 30, tzinfo=utc),
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
