from __future__ import unicode_literals

import datetime

import itertools
from operator import attrgetter

from streamlink.stream.dash_manifest import MPD, MPDParsers, MPDParsingError, utc
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
