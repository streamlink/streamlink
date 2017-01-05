# coding=utf-8
from __future__ import unicode_literals
import sys

from streamlink.stream.hls_playlist import load, StreamInfo, Resolution, Media

if sys.version_info[0:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest

M3U8 = """
#EXTM3U

#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="stereo",LANGUAGE="en",NAME="English",DEFAULT=YES,AUTOSELECT=YES,URI="audio/stereo/en/128kbit.m3u8"
#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="stereo",LANGUAGE="dubbing",NAME="Dubbing",DEFAULT=NO,AUTOSELECT=YES,URI="audio/stereo/none/128kbit.m3u8"

#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="surround",LANGUAGE="en",NAME="English",DEFAULT=YES,AUTOSELECT=YES,URI="audio/surround/en/320kbit.m3u8"
#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="surround",LANGUAGE="dubbing",NAME="Dubbing",DEFAULT=NO,AUTOSELECT=YES,URI="audio/stereo/none/128kbit.m3u8"

#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID="subs",NAME="Deutsch",DEFAULT=NO,AUTOSELECT=YES,FORCED=NO,LANGUAGE="de",URI="subtitles_de.m3u8"
#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID="subs",NAME="English",DEFAULT=YES,AUTOSELECT=YES,FORCED=NO,LANGUAGE="en",URI="subtitles_en.m3u8"
#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID="subs",NAME="Espanol",DEFAULT=NO,AUTOSELECT=YES,FORCED=NO,LANGUAGE="es",URI="subtitles_es.m3u8"
#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID="subs",NAME="Fran\xc3\xa7ais",DEFAULT=NO,AUTOSELECT=YES,FORCED=NO,LANGUAGE="fr",URI="subtitles_fr.m3u8"

#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=258157,CODECS="avc1.4d400d,mp4a.40.2",AUDIO="stereo",RESOLUTION=422x180,SUBTITLES="subs"
video/250kbit.m3u8
#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=520929,CODECS="avc1.4d4015,mp4a.40.2",AUDIO="stereo",RESOLUTION=638x272,SUBTITLES="subs"
video/500kbit.m3u8
#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=831270,CODECS="avc1.4d4015,mp4a.40.2",AUDIO="stereo",RESOLUTION=638x272,SUBTITLES="subs"
video/800kbit.m3u8
#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=1144430,CODECS="avc1.4d401f,mp4a.40.2",AUDIO="surround",RESOLUTION=958x408,SUBTITLES="subs"
video/1100kbit.m3u8
#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=1558322,CODECS="avc1.4d401f,mp4a.40.2",AUDIO="surround",RESOLUTION=1277x554,SUBTITLES="subs"
video/1500kbit.m3u8
#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=4149264,CODECS="avc1.4d4028,mp4a.40.2",AUDIO="surround",RESOLUTION=1921x818,SUBTITLES="subs"
video/4000kbit.m3u8
#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=6214307,CODECS="avc1.4d4028,mp4a.40.2",AUDIO="surround",RESOLUTION=1921x818,SUBTITLES="subs"
video/6000kbit.m3u8
#EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=10285391,CODECS="avc1.4d4033,mp4a.40.2",AUDIO="surround",RESOLUTION=4096x1744,SUBTITLES="subs"
video/10000kbit.m3u8
"""


class TestHLSPlaylist(unittest.TestCase):

    def test_load(self):
        playlist = load(M3U8, "http://test.se/")

        self.assertEqual(playlist.media,
                         [Media(uri='http://test.se/audio/stereo/en/128kbit.m3u8', type='AUDIO', group_id='stereo', language='en',
                                name='English', default=True, autoselect=True, forced=False, characteristics=None),
                          Media(uri='http://test.se/audio/stereo/none/128kbit.m3u8', type='AUDIO', group_id='stereo',
                                language='dubbing', name='Dubbing', default=False, autoselect=True, forced=False,
                                characteristics=None),
                          Media(uri='http://test.se/audio/surround/en/320kbit.m3u8', type='AUDIO', group_id='surround', language='en',
                                name='English', default=True, autoselect=True, forced=False, characteristics=None),
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
                                name='Fran\xc3\xa7ais', default=False, autoselect=True, forced=False,
                                characteristics=None)])

        self.assertEqual([p.stream_info for p in playlist.playlists],
                         [StreamInfo(bandwidth=258157.0, program_id=1, codecs=['avc1.4d400d', 'mp4a.40.2'],
                                     resolution=Resolution(width=422, height=180), audio='stereo', video=None,
                                     subtitles='subs'),
                          StreamInfo(bandwidth=520929.0, program_id=1, codecs=['avc1.4d4015', 'mp4a.40.2'],
                                     resolution=Resolution(width=638, height=272), audio='stereo', video=None,
                                     subtitles='subs'),
                          StreamInfo(bandwidth=831270.0, program_id=1, codecs=['avc1.4d4015', 'mp4a.40.2'],
                                     resolution=Resolution(width=638, height=272), audio='stereo', video=None,
                                     subtitles='subs'),
                          StreamInfo(bandwidth=1144430.0, program_id=1, codecs=['avc1.4d401f', 'mp4a.40.2'],
                                     resolution=Resolution(width=958, height=408), audio='surround', video=None,
                                     subtitles='subs'),
                          StreamInfo(bandwidth=1558322.0, program_id=1, codecs=['avc1.4d401f', 'mp4a.40.2'],
                                     resolution=Resolution(width=1277, height=554), audio='surround', video=None,
                                     subtitles='subs'),
                          StreamInfo(bandwidth=4149264.0, program_id=1, codecs=['avc1.4d4028', 'mp4a.40.2'],
                                     resolution=Resolution(width=1921, height=818), audio='surround', video=None,
                                     subtitles='subs'),
                          StreamInfo(bandwidth=6214307.0, program_id=1, codecs=['avc1.4d4028', 'mp4a.40.2'],
                                     resolution=Resolution(width=1921, height=818), audio='surround', video=None,
                                     subtitles='subs'),
                          StreamInfo(bandwidth=10285391.0, program_id=1, codecs=['avc1.4d4033', 'mp4a.40.2'],
                                     resolution=Resolution(width=4096, height=1744), audio='surround', video=None,
                                     subtitles='subs')])
