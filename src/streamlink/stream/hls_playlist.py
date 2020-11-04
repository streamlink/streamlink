import logging
import re
from binascii import unhexlify
from collections import namedtuple
from datetime import timedelta
from itertools import starmap
from urllib.parse import urljoin, urlparse

from isodate import parse_datetime

log = logging.getLogger(__name__)

__all__ = ["load", "M3U8Parser"]


# EXT-X-BYTERANGE
ByteRange = namedtuple("ByteRange", "range offset")

# EXT-X-DATERANGE
DateRange = namedtuple("DateRange", "id classname start_date end_date duration planned_duration end_on_next x")

# EXT-X-KEY
Key = namedtuple("Key", "method uri iv key_format key_format_versions")

# EXT-X-MAP
Map = namedtuple("Map", "uri byterange")

# EXT-X-MEDIA
Media = namedtuple("Media", "uri type group_id language name default autoselect forced characteristics")

# EXT-X-START
Start = namedtuple("Start", "time_offset precise")

# EXT-X-STREAM-INF
StreamInfo = namedtuple("StreamInfo", "bandwidth program_id codecs resolution audio video subtitles")

# EXT-X-I-FRAME-STREAM-INF
IFrameStreamInfo = namedtuple("IFrameStreamInfo", "bandwidth program_id codecs resolution video")

Playlist = namedtuple("Playlist", "uri stream_info media is_iframe")
Resolution = namedtuple("Resolution", "width height")
Segment = namedtuple("Segment", "uri duration title key discontinuity byterange date map")


class M3U8:
    def __init__(self):
        self.is_endlist = False
        self.is_master = False

        self.allow_cache = None
        self.discontinuity_sequence = None
        self.iframes_only = None
        self.media_sequence = None
        self.playlist_type = None
        self.target_duration = None
        self.start = None
        self.version = None

        self.media = []
        self.playlists = []
        self.dateranges = []
        self.segments = []

    @classmethod
    def is_date_in_daterange(cls, date, daterange):
        if date is None or daterange.start_date is None:
            return None

        if daterange.end_date is not None:
            return daterange.start_date <= date < daterange.end_date

        duration = daterange.duration or daterange.planned_duration
        if duration is not None:
            end = daterange.start_date + duration
            return daterange.start_date <= date < end

        return daterange.start_date <= date


class M3U8Parser:
    _extinf_re = re.compile(r"(?P<duration>\d+(\.\d+)?)(,(?P<title>.+))?")
    _attr_re = re.compile(r"([A-Z\-]+)=(\d+\.\d+|0x[0-9A-z]+|\d+x\d+|\d+|\"(.+?)\"|[0-9A-z\-]+)")
    _range_re = re.compile(r"(?P<range>\d+)(@(?P<offset>.+))?")
    _tag_re = re.compile(r"#(?P<tag>[\w-]+)(:(?P<value>.+))?")
    _res_re = re.compile(r"(\d+)x(\d+)")

    def __init__(self, base_uri=None, m3u8=M3U8, **kwargs):
        self.base_uri = base_uri
        self.m3u8 = m3u8()
        self.state = {}

    def create_stream_info(self, streaminf, cls=None):
        program_id = streaminf.get("PROGRAM-ID")

        bandwidth = streaminf.get("BANDWIDTH")
        if bandwidth:
            bandwidth = float(bandwidth)

        resolution = streaminf.get("RESOLUTION")
        if resolution:
            resolution = self.parse_resolution(resolution)

        codecs = streaminf.get("CODECS")
        if codecs:
            codecs = codecs.split(",")
        else:
            codecs = []

        if cls == IFrameStreamInfo:
            return IFrameStreamInfo(bandwidth, program_id, codecs, resolution,
                                    streaminf.get("VIDEO"))
        else:
            return StreamInfo(bandwidth, program_id, codecs, resolution,
                              streaminf.get("AUDIO"), streaminf.get("VIDEO"),
                              streaminf.get("SUBTITLES"))

    def split_tag(self, line):
        match = self._tag_re.match(line)

        if match:
            return match.group("tag"), (match.group("value") or "").strip()

        return None, None

    def parse_attributes(self, value):
        def map_attribute(key, value, quoted):
            return (key, quoted or value)

        attr = self._attr_re.findall(value)

        return dict(starmap(map_attribute, attr))

    def parse_bool(self, value):
        return value == "YES"

    def parse_byterange(self, value):
        match = self._range_re.match(value)

        if match:
            return ByteRange(int(match.group("range")),
                             int(match.group("offset") or 0))

    def parse_extinf(self, value):
        match = self._extinf_re.match(value)
        if match:
            return float(match.group("duration")), match.group("title")
        return (0, None)

    def parse_hex(self, value):
        value = value[2:]
        if len(value) % 2:
            value = "0" + value

        return unhexlify(value)

    def parse_iso8601(self, value):
        if value is None:
            return None
        try:
            return parse_datetime(value)
        except ValueError:
            return None

    def parse_timedelta(self, value):
        return timedelta(seconds=float(value)) if value is not None else None

    def parse_resolution(self, value):
        match = self._res_re.match(value)

        if match:
            width, height = int(match.group(1)), int(match.group(2))
        else:
            width, height = 0, 0

        return Resolution(width, height)

    def parse_tag_extinf(self, value):
        self.state["expect_segment"] = True
        self.state["extinf"] = self.parse_extinf(value)

    def parse_tag_ext_x_byterange(self, value):
        self.state["expect_segment"] = True
        self.state["byterange"] = self.parse_byterange(value)

    def parse_tag_ext_x_targetduration(self, value):
        self.m3u8.target_duration = int(value)

    def parse_tag_ext_x_media_sequence(self, value):
        self.m3u8.media_sequence = int(value)

    def parse_tag_ext_x_key(self, value):
        attr = self.parse_attributes(value)
        iv = attr.get("IV")
        if iv:
            iv = self.parse_hex(iv)
        self.state["key"] = Key(attr.get("METHOD"),
                                self.uri(attr.get("URI")),
                                iv, attr.get("KEYFORMAT"),
                                attr.get("KEYFORMATVERSIONS"))

    def parse_tag_ext_x_program_date_time(self, value):
        self.state["date"] = self.parse_iso8601(value)

    def parse_tag_ext_x_daterange(self, value):
        attr = self.parse_attributes(value)
        daterange = DateRange(
            attr.pop("ID", None),
            attr.pop("CLASS", None),
            self.parse_iso8601(attr.pop("START-DATE", None)),
            self.parse_iso8601(attr.pop("END-DATE", None)),
            self.parse_timedelta(attr.pop("DURATION", None)),
            self.parse_timedelta(attr.pop("PLANNED-DURATION", None)),
            self.parse_bool(attr.pop("END-ON-NEXT", None)),
            attr
        )
        self.m3u8.dateranges.append(daterange)

    def parse_tag_ext_x_allow_cache(self, value):
        self.m3u8.allow_cache = self.parse_bool(value)

    def parse_tag_ext_x_stream_inf(self, value):
        self.state["streaminf"] = self.parse_attributes(value)
        self.state["expect_playlist"] = True

    def parse_tag_ext_x_playlist_type(self, value):
        self.m3u8.playlist_type = value

    def parse_tag_ext_x_endlist(self, value):
        self.m3u8.is_endlist = True

    def parse_tag_ext_x_media(self, value):
        attr = self.parse_attributes(value)
        media = Media(
            self.uri(attr.get("URI")),
            attr.get("TYPE"),
            attr.get("GROUP-ID"),
            attr.get("LANGUAGE"),
            attr.get("NAME"),
            self.parse_bool(attr.get("DEFAULT")),
            self.parse_bool(attr.get("AUTOSELECT")),
            self.parse_bool(attr.get("FORCED")),
            attr.get("CHARACTERISTICS")
        )
        self.m3u8.media.append(media)

    def parse_tag_ext_x_discontinuity(self, value):
        self.state["discontinuity"] = True
        self.state["map"] = None

    def parse_tag_ext_x_discontinuity_sequence(self, value):
        self.m3u8.discontinuity_sequence = int(value)

    def parse_tag_ext_x_i_frames_only(self, value):
        self.m3u8.iframes_only = True

    def parse_tag_ext_x_map(self, value):
        attr = self.parse_attributes(value)
        byterange = self.parse_byterange(attr.get("BYTERANGE", ""))
        self.state["map"] = Map(attr.get("URI"), byterange)

    def parse_tag_ext_x_i_frame_stream_inf(self, value):
        attr = self.parse_attributes(value)
        streaminf = self.state.pop("streaminf", attr)
        stream_info = self.create_stream_info(streaminf, IFrameStreamInfo)
        playlist = Playlist(self.uri(attr.get("URI")), stream_info, [], True)
        self.m3u8.playlists.append(playlist)

    def parse_tag_ext_x_version(self, value):
        self.m3u8.version = int(value)

    def parse_tag_ext_x_start(self, value):
        attr = self.parse_attributes(value)
        start = Start(attr.get("TIME-OFFSET"),
                      self.parse_bool(attr.get("PRECISE", "NO")))
        self.m3u8.start = start

    def parse_line(self, line):
        if line.startswith("#"):
            tag, value = self.split_tag(line)
            if not tag:
                return
            method = "parse_tag_" + tag.lower().replace("-", "_")
            if not hasattr(self, method):
                return
            getattr(self, method)(value)
        elif self.state.pop("expect_segment", None):
            segment = self.get_segment(self.uri(line))
            self.m3u8.segments.append(segment)
        elif self.state.pop("expect_playlist", None):
            playlist = self.get_playlist(self.uri(line))
            self.m3u8.playlists.append(playlist)

    def parse(self, data):
        lines = iter(filter(bool, data.splitlines()))
        try:
            line = next(lines)
        except StopIteration:
            return self.m3u8
        else:
            if not line.startswith("#EXTM3U"):
                log.warning("Malformed HLS Playlist. Expected #EXTM3U, but got {0}".format(line[:250]))
                raise ValueError("Missing #EXTM3U header")

        parse_line = self.parse_line
        for line in lines:
            parse_line(line)

        # Associate Media entries with each Playlist
        for playlist in self.m3u8.playlists:
            for media_type in ("audio", "video", "subtitles"):
                group_id = getattr(playlist.stream_info, media_type, None)
                if group_id:
                    for media in filter(lambda m: m.group_id == group_id,
                                        self.m3u8.media):
                        playlist.media.append(media)

        self.m3u8.is_master = not not self.m3u8.playlists

        return self.m3u8

    def uri(self, uri):
        if uri and urlparse(uri).scheme:
            return uri
        elif self.base_uri and uri:
            return urljoin(self.base_uri, uri)
        else:
            return uri

    def get_segment(self, uri):
        byterange = self.state.pop("byterange", None)
        extinf = self.state.pop("extinf", (0, None))
        date = self.state.pop("date", None)
        map_ = self.state.get("map")
        key = self.state.get("key")
        discontinuity = self.state.pop("discontinuity", False)

        return Segment(
            uri,
            extinf[0],
            extinf[1],
            key,
            discontinuity,
            byterange,
            date,
            map_
        )

    def get_playlist(self, uri):
        streaminf = self.state.pop("streaminf", {})
        stream_info = self.create_stream_info(streaminf)
        return Playlist(uri, stream_info, [], False)


def load(data, base_uri=None, parser=M3U8Parser, **kwargs):
    """Attempts to parse a M3U8 playlist from a string of data.

    If specified, *base_uri* is the base URI that relative URIs will
    be joined together with, otherwise relative URIs will be as is.

    If specified, *parser* can be a M3U8Parser subclass to be used
    to parse the data.

    """
    return parser(base_uri, **kwargs).parse(data)
