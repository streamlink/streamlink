import re

from collections import namedtuple
from io import BytesIO
try:
    from Crypto.Cipher import AES
    CAN_DECRYPT = True
except ImportError:
    CAN_DECRYPT = False

from streamlink.compat import range
from streamlink.exceptions import StreamError
from streamlink.packages.flashmedia.tag import (
    AACAudioData, AudioData, AVCVideoData, RawData, Tag, VideoData
)
from streamlink.packages.flashmedia.tag import (
    AAC_PACKET_TYPE_RAW, AAC_PACKET_TYPE_SEQUENCE_HEADER,
    AUDIO_BIT_RATE_16, AUDIO_CODEC_ID_AAC, AUDIO_RATE_44_KHZ, AUDIO_TYPE_STEREO,
    AVC_PACKET_TYPE_NALU, AVC_PACKET_TYPE_SEQUENCE_HEADER,
    TAG_TYPE_AUDIO, TAG_TYPE_VIDEO, VIDEO_CODEC_ID_AVC,
    VIDEO_FRAME_TYPE_INTER_FRAME, VIDEO_FRAME_TYPE_KEY_FRAME
)
from streamlink.packages.flashmedia.types import U8, U16BE, U32BE
from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import Stream, StreamIOIterWrapper
from streamlink.stream.flvconcat import FLVTagConcat
from streamlink.stream.segmented import (
    SegmentedStreamReader, SegmentedStreamWriter, SegmentedStreamWorker
)

HEADERS = {"User-Agent": "Mozilla/5.0"}
BEAT_PROGRAM = "http://www.be-at.tv/{0}.program"
BEAT_URL = "http://www.be-at.tv/{0}/{1}/{2}.{3}"
QUALITY_MAP = {
    "audio_mono": 0,
    "audio_stereo": 1,
    "mobile_low": 5,
    "mobile_medium": 6,
    "web_medium": 10,
    "web_high": 11,
    "web_hd": 12
}

_url_re = re.compile("http(s)?://(\w+\.)?be-at.tv/")
_schema = validate.Schema(
    validate.any(
        None,
        {
            "status": int,
            "media": [{
                "duration": validate.any(float, int),
                "offset": validate.any(float, int),
                "id": int,
                "parts": [{
                    "duration": validate.any(float, int),
                    "id": int,
                    "offset": validate.any(float, int),
                    validate.optional("recording"): int,
                    validate.optional("start"): validate.any(float, int)
                }]
            }]
        }
    )
)

Chunk = namedtuple("Chunk", "recording quality sequence extension")


class BeatFLVTagConcat(FLVTagConcat):
    def __init__(self, *args, **kwargs):
        FLVTagConcat.__init__(self, *args, **kwargs)

    def decrypt_data(self, key, iv, data):
        decryptor = AES.new(key, AES.MODE_CBC, iv)
        return decryptor.decrypt(data)

    def iter_tags(self, fd=None, buf=None, skip_header=None):
        flags = U8.read(fd)
        quality = flags & 15
        version = flags >> 4
        lookup_size = U16BE.read(fd)
        enc_table = fd.read(lookup_size)

        key = b""
        iv = b""

        for i in range(16):
            key += fd.read(1)
            iv += fd.read(1)

        if not (key and iv):
            return

        dec_table = self.decrypt_data(key, iv, enc_table)
        dstream = BytesIO(dec_table)

        # Decode lookup table (ported from K-S-V BeatConvert.php)
        while True:
            flags = U8.read(dstream)
            if not flags:
                break

            typ = flags >> 4
            encrypted = (flags & 4) > 0
            keyframe = (flags & 2) > 0
            config = (flags & 1) > 0
            time = U32BE.read(dstream)
            data_length = U32BE.read(dstream)

            if encrypted:
                raw_length = U32BE.read(dstream)
            else:
                raw_length = data_length

            # Decrypt encrypted tags
            data = fd.read(data_length)
            if encrypted:
                data = self.decrypt_data(key, iv, data)
                data = data[:raw_length]

            # Create video tag
            if typ == 1:
                if version == 2:
                    if config:
                        avc = AVCVideoData(AVC_PACKET_TYPE_SEQUENCE_HEADER,
                                           data=data)
                    else:
                        avc = AVCVideoData(AVC_PACKET_TYPE_NALU, data=data)

                    if keyframe:
                        videodata = VideoData(VIDEO_FRAME_TYPE_KEY_FRAME,
                                              VIDEO_CODEC_ID_AVC, avc)
                    else:
                        videodata = VideoData(VIDEO_FRAME_TYPE_INTER_FRAME,
                                              VIDEO_CODEC_ID_AVC, avc)
                else:
                    videodata = RawData(data)

                yield Tag(TAG_TYPE_VIDEO, time, videodata)

            # Create audio tag
            if typ == 2:
                if version == 2:
                    if config:
                        aac = AACAudioData(AAC_PACKET_TYPE_SEQUENCE_HEADER,
                                           data)
                    else:
                        aac = AACAudioData(AAC_PACKET_TYPE_RAW, data)

                    audiodata = AudioData(codec=AUDIO_CODEC_ID_AAC,
                                          rate=AUDIO_RATE_44_KHZ,
                                          bits=AUDIO_BIT_RATE_16,
                                          type=AUDIO_TYPE_STEREO,
                                          data=aac)
                else:
                    audiodata = RawData(data)

                yield Tag(TAG_TYPE_AUDIO, time, audiodata)


class BeatStreamWriter(SegmentedStreamWriter):
    def __init__(self, *args, **kwargs):
        SegmentedStreamWriter.__init__(self, *args, **kwargs)

        self.concater = BeatFLVTagConcat(flatten_timestamps=True)

    def fetch(self, chunk, retries=None):
        if self.closed or not retries:
            return

        try:
            url = BEAT_URL.format(chunk.recording,
                                  chunk.quality,
                                  chunk.sequence,
                                  chunk.extension)

            return self.session.http.get(url,
                                         headers=HEADERS,
                                         timeout=self.timeout,
                                         exception=StreamError)
        except StreamError as err:
            self.logger.error(
                "Failed to open chunk {0}/{1}/{2}: {3}",
                chunk.recording, chunk.quality, chunk.sequence, err
            )
            return self.fetch(chunk, retries - 1)

    def write(self, chunk, res, chunk_size=8192):
        try:
            fd = StreamIOIterWrapper(res.iter_content(chunk_size))
            for data in self.concater.iter_chunks(fd=fd, skip_header=True):
                self.reader.buffer.write(data)
                if self.closed:
                    return

            self.logger.debug("Download of chunk {0}/{1}/{2} complete",
                              chunk.recording,
                              chunk.quality,
                              chunk.sequence)
        except IOError as err:
            self.logger.error("Failed to read chunk {0}/{1}/{2}: {3}",
                              chunk.recording,
                              chunk.quality,
                              chunk.sequence, err)


class BeatStreamWorker(SegmentedStreamWorker):
    def __init__(self, *args, **kwargs):
        SegmentedStreamWorker.__init__(self, *args, **kwargs)

    def iter_segments(self):
        quality = QUALITY_MAP[self.stream.quality]
        for part in self.stream.parts:
            duration = part["duration"]
            if not part.get("recording"):
                recording = part["id"]
                extension = "part"
            else:
                recording = part["recording"]
                extension = "rec"

            chunks = int(duration / 12) + 1
            start = int(part.get("start", 0) / 12)
            for sequence in range(start, chunks + start):
                if self.closed:
                    return

                self.logger.debug("Adding chunk {0}/{1}/{2} to queue",
                                  recording, quality, sequence)

                yield Chunk(recording, quality, sequence, extension)


class BeatStreamReader(SegmentedStreamReader):
    __worker__ = BeatStreamWorker
    __writer__ = BeatStreamWriter

    def __init__(self, stream, *args, **kwargs):
        self.logger = stream.session.logger.new_module("stream.beat")

        SegmentedStreamReader.__init__(self, stream, *args, **kwargs)


class BeatStream(Stream):
    __shortname__ = "beat"

    def __init__(self, session, parts, quality):
        Stream.__init__(self, session)

        self.parts = parts
        self.quality = quality

    def __repr__(self):
        return ("<BeatStream({0!r}, {1!r}>").format(len(self.parts),
                                                    self.quality)

    def __json__(self):
        return dict(parts=self.parts, quality=self.quality,
                    **Stream.__json__(self))

    def open(self):
        if not CAN_DECRYPT:
            raise StreamError(
                "pyCrypto needs to be installed to decrypt this stream"
            )

        reader = BeatStreamReader(self)
        reader.open()

        return reader


class BeatTV(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    @classmethod
    def stream_weight(cls, key):
        weight = QUALITY_MAP.get(key)
        if weight:
            return weight, "beat"

        return Plugin.stream_weight(key)

    def _get_stream_info(self, url):
        res = http.get(url, headers=HEADERS)
        match = re.search("embed.swf\?p=(\d+)", res.text)
        if not match:
            return
        program = match.group(1)
        res = http.get(BEAT_PROGRAM.format(program), headers=HEADERS)

        return http.json(res, schema=_schema)

    def _get_streams(self):
        info = self._get_stream_info(self.url)
        if not info or info["status"] == 0:
            return

        parts = []
        for media in info["media"]:
            if not media["id"]:
                continue

            for part in media["parts"]:
                if not part["duration"]:
                    continue

                parts.append(part)

        if not parts:
            return

        streams = {}
        for quality in QUALITY_MAP:
            streams[quality] = BeatStream(self.session, parts, quality)

        return streams


__plugin__ = BeatTV
