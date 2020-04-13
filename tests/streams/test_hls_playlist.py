# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from streamlink.stream.hls_playlist import load, StreamInfo, Resolution, Media
import unittest
from tests.resources import text


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
                StreamInfo(bandwidth=258157.0, program_id='1', codecs=['avc1.4d400d', 'mp4a.40.2'],
                           resolution=Resolution(width=422, height=180), audio='stereo', video=None,
                           subtitles='subs'),
                StreamInfo(bandwidth=520929.0, program_id='1', codecs=['avc1.4d4015', 'mp4a.40.2'],
                           resolution=Resolution(width=638, height=272), audio='stereo', video=None,
                           subtitles='subs'),
                StreamInfo(bandwidth=831270.0, program_id='1', codecs=['avc1.4d4015', 'mp4a.40.2'],
                           resolution=Resolution(width=638, height=272), audio='stereo', video=None,
                           subtitles='subs'),
                StreamInfo(bandwidth=1144430.0, program_id='1', codecs=['avc1.4d401f', 'mp4a.40.2'],
                           resolution=Resolution(width=958, height=408), audio='surround', video=None,
                           subtitles='subs'),
                StreamInfo(bandwidth=1558322.0, program_id='1', codecs=['avc1.4d401f', 'mp4a.40.2'],
                           resolution=Resolution(width=1277, height=554), audio='surround', video=None,
                           subtitles='subs'),
                StreamInfo(bandwidth=4149264.0, program_id='1', codecs=['avc1.4d4028', 'mp4a.40.2'],
                           resolution=Resolution(width=1921, height=818), audio='surround', video=None,
                           subtitles='subs'),
                StreamInfo(bandwidth=6214307.0, program_id='1', codecs=['avc1.4d4028', 'mp4a.40.2'],
                           resolution=Resolution(width=1921, height=818), audio='surround', video=None,
                           subtitles='subs'),
                StreamInfo(bandwidth=10285391.0, program_id='1', codecs=['avc1.4d4033', 'mp4a.40.2'],
                           resolution=Resolution(width=4096, height=1744), audio='surround', video=None,
                           subtitles='subs')
            ]
        )
