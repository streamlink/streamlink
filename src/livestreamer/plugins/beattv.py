import re

from collections import namedtuple
try:
    from Crypto.Cipher import AES
    CAN_DECRYPT = True
except ImportError:
    CAN_DECRYPT = False
from io import BytesIO

from livestreamer.compat import range
from livestreamer.exceptions import StreamError, PluginError
from livestreamer.packages.flashmedia.tag import (AACAudioData, AudioData,
                                                  AVCVideoData, RawData, Tag,
                                                  VideoData)
from livestreamer.packages.flashmedia.tag import (AAC_PACKET_TYPE_RAW,
                                                  AAC_PACKET_TYPE_SEQUENCE_HEADER,
                                                  AUDIO_BIT_RATE_16,
                                                  AUDIO_CODEC_ID_AAC,
                                                  AUDIO_RATE_44_KHZ,
                                                  AUDIO_TYPE_STEREO,
                                                  AVC_PACKET_TYPE_NALU,
                                                  AVC_PACKET_TYPE_SEQUENCE_HEADER,
                                                  TAG_TYPE_AUDIO,
                                                  TAG_TYPE_VIDEO,
                                                  VIDEO_CODEC_ID_AVC,
                                                  VIDEO_FRAME_TYPE_INTER_FRAME,
                                                  VIDEO_FRAME_TYPE_KEY_FRAME)
from livestreamer.packages.flashmedia.types import U8, U16BE, U32BE
from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http
from livestreamer.stream import Stream, StreamIOIterWrapper
from livestreamer.stream.flvconcat import FLVTagConcat
from livestreamer.stream.segmented import (SegmentedStreamReader,
                                           SegmentedStreamWriter,
                                           SegmentedStreamWorker)


HEADERS = {"User-Agent": "Mozilla/5.0"}
BEAT_PROGRAM = "http://www.be-at.tv/{0}.program"
BEAT_URL = "http://www.be-at.tv/{0}/{1}/{2}.{3}"

QUALITY_MAP = {"audio_mono": 0, "audio_stereo": 1,
               "mobile_low": 5, "mobile_medium": 6,
               "web_medium": 10, "web_high": 11, "web_hd": 12}

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

    def open_chunk(self, chunk, retries=3):
        while retries and not self.closed:
            try:
                url = BEAT_URL.format(chunk.recording,
                                      chunk.quality,
                                      chunk.sequence,
                                      chunk.extension)
                return self.session.http.get(url,
                                             stream=True,
                                             headers=HEADERS,
                                             timeout=10,
                                             exception=StreamError)
            except StreamError as err:
                self.logger.error("Failed to open chunk {0}/{1}/{2}: {3}",
                                  chunk.recording,
                                  chunk.quality,
                                  chunk.sequence, err)
            retries -= 1

    def write(self, chunk, chunk_size=8192):
        res = self.open_chunk(chunk)
        if not res:
            return

        try:
            fd = StreamIOIterWrapper(res.iter_content(8192))
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
            duration = part.get("duration")
            if not part.get("recording"):
                recording = part.get("id")
                extension = "part"
            else:
                recording = part.get("recording")
                extension = "rec"
            chunks = int(duration / 12) + 1
            start = int(part.get("start", 0) / 12)
            for sequence in range(start, chunks + start):
                if self.closed:
                    return
                self.logger.debug("Adding chunk {0}/{1}/{2} to queue",
                                  recording,
                                  quality,
                                  sequence)
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
        reader = BeatStreamReader(self)
        reader.open()

        return reader


class BeatTV(Plugin):

    @classmethod
    def can_handle_url(self, url):
        return "be-at.tv" in url

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

        return http.json(res)

    def _get_streams(self):
        if not CAN_DECRYPT:
            raise PluginError("Need pyCrypto installed to decrypt streams")

        json = self._get_stream_info(self.url)

        if not json:
            return

        if json.get("status", 0) == 0:
            return

        parts = []
        for media in json.get("media", []):
            if media.get("id") < 0:
                continue
            for part in media.get("parts", []):
                if part.get("duration") < 0:
                    continue
                parts.append(part)

        if not parts:
            return

        streams = {}
        for quality in QUALITY_MAP:
            streams[quality] = BeatStream(self.session, parts, quality)

        return streams


__plugin__ = BeatTV
