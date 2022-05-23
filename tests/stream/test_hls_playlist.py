import unittest
from datetime import datetime, timedelta

from isodate import tzinfo  # type: ignore[import]

from streamlink.stream.hls_playlist import DateRange, M3U8Parser, Media, Resolution, Segment, StreamInfo, load
from tests.resources import text


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


class TestHLSPlaylist(unittest.TestCase):
    def test_load(self):
        with text("hls/test_1.m3u8") as m3u8_fh:
            playlist = load(m3u8_fh.read(), "http://test.se/")

        self.assertEqual(
            playlist.media,
            [
                Media(uri='http://test.se/audio/stereo/en/128kbit.m3u8', type='AUDIO', group_id='stereo',
                      language='en', name='English', default=True, autoselect=True, forced=False,
                      characteristics=None),
                Media(uri='http://test.se/audio/stereo/none/128kbit.m3u8', type='AUDIO', group_id='stereo',
                      language='dubbing', name='Dubbing', default=False, autoselect=True, forced=False,
                      characteristics=None),
                Media(uri='http://test.se/audio/surround/en/320kbit.m3u8', type='AUDIO', group_id='surround',
                      language='en', name='English', default=True, autoselect=True, forced=False,
                      characteristics=None),
                Media(uri='http://test.se/audio/stereo/none/128kbit.m3u8', type='AUDIO', group_id='surround',
                      language='dubbing', name='Dubbing', default=False, autoselect=True, forced=False,
                      characteristics=None),
                Media(uri='http://test.se/subtitles_de.m3u8', type='SUBTITLES', group_id='subs', language='de',
                      name='Deutsch', default=False, autoselect=True, forced=False, characteristics=None),
                Media(uri='http://test.se/subtitles_en.m3u8', type='SUBTITLES', group_id='subs', language='en',
                      name='English', default=True, autoselect=True, forced=False, characteristics=None),
                Media(uri='http://test.se/subtitles_es.m3u8', type='SUBTITLES', group_id='subs', language='es',
                      name='Espanol', default=False, autoselect=True, forced=False, characteristics=None),
                Media(uri='http://test.se/subtitles_fr.m3u8', type='SUBTITLES', group_id='subs', language='fr',
                      name='Français', default=False, autoselect=True, forced=False, characteristics=None)
            ]
        )

        self.assertEqual(
            [p.stream_info for p in playlist.playlists],
            [
                StreamInfo(bandwidth=260000, program_id='1', codecs=['avc1.4d400d', 'mp4a.40.2'],
                           resolution=Resolution(width=422, height=180), audio='stereo', video=None,
                           subtitles='subs'),
                StreamInfo(bandwidth=520000, program_id='1', codecs=['avc1.4d4015', 'mp4a.40.2'],
                           resolution=Resolution(width=638, height=272), audio='stereo', video=None,
                           subtitles='subs'),
                StreamInfo(bandwidth=830000, program_id='1', codecs=['avc1.4d4015', 'mp4a.40.2'],
                           resolution=Resolution(width=638, height=272), audio='stereo', video=None,
                           subtitles='subs'),
                StreamInfo(bandwidth=1100000, program_id='1', codecs=['avc1.4d401f', 'mp4a.40.2'],
                           resolution=Resolution(width=958, height=408), audio='surround', video=None,
                           subtitles='subs'),
                StreamInfo(bandwidth=1600000, program_id='1', codecs=['avc1.4d401f', 'mp4a.40.2'],
                           resolution=Resolution(width=1277, height=554), audio='surround', video=None,
                           subtitles='subs'),
                StreamInfo(bandwidth=4100000, program_id='1', codecs=['avc1.4d4028', 'mp4a.40.2'],
                           resolution=Resolution(width=1921, height=818), audio='surround', video=None,
                           subtitles='subs'),
                StreamInfo(bandwidth=6200000, program_id='1', codecs=['avc1.4d4028', 'mp4a.40.2'],
                           resolution=Resolution(width=1921, height=818), audio='surround', video=None,
                           subtitles='subs'),
                StreamInfo(bandwidth=10000000, program_id='1', codecs=['avc1.4d4033', 'mp4a.40.2'],
                           resolution=Resolution(width=4096, height=1744), audio='surround', video=None,
                           subtitles='subs')
            ]
        )

    def test_parse_date(self):
        with text("hls/test_date.m3u8") as m3u8_fh:
            playlist = load(m3u8_fh.read(), "http://test.se/")

        start_date = datetime(year=2000, month=1, day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=tzinfo.UTC)
        end_date = datetime(year=2000, month=1, day=1, hour=0, minute=1, second=0, microsecond=0, tzinfo=tzinfo.UTC)
        delta_15 = timedelta(seconds=15)
        delta_30 = timedelta(seconds=30, milliseconds=500)
        delta_60 = timedelta(seconds=60)

        self.assertEqual(playlist.target_duration, 120)

        self.assertEqual(
            [daterange for daterange in playlist.dateranges],
            [
                DateRange(id="start-invalid",
                          start_date=None,
                          classname=None, end_date=None, duration=None, planned_duration=None, end_on_next=False, x={}),
                DateRange(id="start-no-frac",
                          start_date=start_date,
                          classname=None, end_date=None, duration=None, planned_duration=None, end_on_next=False, x={}),
                DateRange(id="start-with-frac",
                          start_date=start_date,
                          classname=None, end_date=None, duration=None, planned_duration=None, end_on_next=False, x={}),
                DateRange(id="with-class",
                          start_date=start_date, classname="bar",
                          end_date=None, duration=None, planned_duration=None, end_on_next=False, x={}),
                DateRange(id="duration",
                          start_date=start_date, duration=delta_30,
                          classname=None, end_date=None, planned_duration=None, end_on_next=False, x={}),
                DateRange(id="planned-duration",
                          start_date=start_date, planned_duration=delta_15,
                          classname=None, end_date=None, duration=None, end_on_next=False, x={}),
                DateRange(id="duration-precedence",
                          start_date=start_date, duration=delta_30, planned_duration=delta_15,
                          classname=None, end_date=None, end_on_next=False, x={}),
                DateRange(id="end",
                          start_date=start_date, end_date=end_date,
                          classname=None, duration=None, planned_duration=None, end_on_next=False, x={}),
                DateRange(id="end-precedence",
                          start_date=start_date, end_date=end_date, duration=delta_30,
                          classname=None, planned_duration=None, end_on_next=False, x={}),
                DateRange(x={"X-CUSTOM": "value"},
                          id=None, start_date=None, end_date=None, duration=None,
                          classname=None, planned_duration=None, end_on_next=False)
            ]
        )
        self.assertEqual(
            [segment for segment in playlist.segments],
            [
                Segment(uri="http://test.se/segment0-15.ts", duration=15.0, title="live", date=start_date,
                        key=None, discontinuity=False, byterange=None, map=None),
                Segment(uri="http://test.se/segment15-30.5.ts", duration=15.5, title="live", date=start_date + delta_15,
                        key=None, discontinuity=False, byterange=None, map=None),
                Segment(uri="http://test.se/segment30.5-60.ts", duration=29.5, title="live", date=start_date + delta_30,
                        key=None, discontinuity=False, byterange=None, map=None),
                Segment(uri="http://test.se/segment60-.ts", duration=60.0, title="live", date=start_date + delta_60,
                        key=None, discontinuity=False, byterange=None, map=None)
            ]
        )

        self.assertEqual(
            [playlist.is_date_in_daterange(playlist.segments[0].date, daterange) for daterange in playlist.dateranges],
            [None, True, True, True, True, True, True, True, True, None]
        )
        self.assertEqual(
            [playlist.is_date_in_daterange(playlist.segments[1].date, daterange) for daterange in playlist.dateranges],
            [None, True, True, True, True, False, True, True, True, None]
        )
        self.assertEqual(
            [playlist.is_date_in_daterange(playlist.segments[2].date, daterange) for daterange in playlist.dateranges],
            [None, True, True, True, False, False, False, True, True, None]
        )
        self.assertEqual(
            [playlist.is_date_in_daterange(playlist.segments[3].date, daterange) for daterange in playlist.dateranges],
            [None, True, True, True, False, False, False, False, False, None]
        )
