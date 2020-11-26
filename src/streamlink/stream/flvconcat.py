import logging
from collections import namedtuple
from io import IOBase
from itertools import chain, islice
from threading import Thread

from streamlink.buffers import RingBuffer
from streamlink.packages.flashmedia import FLVError
from streamlink.packages.flashmedia.tag import (
    AACAudioData, AAC_PACKET_TYPE_SEQUENCE_HEADER, AUDIO_CODEC_ID_AAC, AVCVideoData,
    AVC_PACKET_TYPE_SEQUENCE_HEADER, AudioData, Header, ScriptData, TAG_TYPE_AUDIO,
    TAG_TYPE_VIDEO, Tag, VIDEO_CODEC_ID_AVC, VideoCommandFrame, VideoData
)

__all__ = ["extract_flv_header_tags", "FLVTagConcat", "FLVTagConcatIO"]
log = logging.getLogger(__name__)
FLVHeaderTags = namedtuple("FLVHeaderTags", "metadata aac vc")


def iter_flv_tags(fd=None, buf=None, strict=False, skip_header=False):
    if not (fd or buf):
        return

    offset = 0
    if not skip_header:
        if fd:
            Header.deserialize(fd)
        elif buf:
            header, offset = Header.deserialize_from(buf, offset)

    while fd or buf and offset < len(buf):
        try:
            if fd:
                tag = Tag.deserialize(fd, strict=strict)
            elif buf:
                tag, offset = Tag.deserialize_from(buf, offset, strict=strict)
        except (OSError, FLVError) as err:
            if "Insufficient tag header" in str(err):
                break

            raise OSError(err)

        yield tag


def extract_flv_header_tags(stream):
    fd = stream.open()
    metadata = aac_header = avc_header = None

    for tag_index, tag in enumerate(iter_flv_tags(fd)):
        if isinstance(tag.data, ScriptData) and tag.data.name == "onMetaData":
            metadata = tag
        elif (isinstance(tag.data, VideoData) and isinstance(tag.data.data, AVCVideoData)):
            if tag.data.data.type == AVC_PACKET_TYPE_SEQUENCE_HEADER:
                avc_header = tag
        elif (isinstance(tag.data, AudioData) and isinstance(tag.data.data, AACAudioData)):
            if tag.data.data.type == AAC_PACKET_TYPE_SEQUENCE_HEADER:
                aac_header = tag

        if aac_header and avc_header and metadata:
            break

        # Give up after 10 tags
        if tag_index == 9:
            break

    return FLVHeaderTags(metadata, aac_header, avc_header)


class FLVTagConcat:
    def __init__(self, duration=None, tags=[], has_video=True, has_audio=True,
                 flatten_timestamps=False, sync_headers=False):
        self.duration = duration
        self.flatten_timestamps = flatten_timestamps
        self.has_audio = has_audio
        self.has_video = has_video
        self.sync_headers = sync_headers
        self.tags = tags

        if not (has_audio and has_video):
            self.sync_headers = False

        self.audio_header_written = False
        self.flv_header_written = False
        self.video_header_written = False
        self.timestamps_add = {}
        self.timestamps_orig = {}
        self.timestamps_sub = {}

    @property
    def headers_written(self):
        return self.audio_header_written and self.video_header_written

    def verify_tag(self, tag):
        if tag.filter:
            raise OSError("Tag has filter flag set, probably encrypted")

        # Only AAC and AVC has detectable headers
        if isinstance(tag.data, AudioData) and tag.data.codec != AUDIO_CODEC_ID_AAC:
            self.audio_header_written = True
        if isinstance(tag.data, VideoData) and tag.data.codec != VIDEO_CODEC_ID_AVC:
            self.video_header_written = True

        # Make sure there is no timestamp gap between audio and video when syncing
        if self.sync_headers and self.timestamps_sub and not self.headers_written:
            self.timestamps_sub = {}

        if isinstance(tag.data, AudioData):
            if isinstance(tag.data.data, AACAudioData):
                if tag.data.data.type == AAC_PACKET_TYPE_SEQUENCE_HEADER:
                    if self.audio_header_written:
                        return

                    self.audio_header_written = True
                else:
                    if self.sync_headers and not self.headers_written:
                        return

                    if not self.audio_header_written:
                        return
            else:
                if self.sync_headers and not self.headers_written:
                    return

        elif isinstance(tag.data, VideoData):
            if isinstance(tag.data.data, AVCVideoData):
                if tag.data.data.type == AVC_PACKET_TYPE_SEQUENCE_HEADER:
                    if self.video_header_written:
                        return

                    self.video_header_written = True
                else:
                    if self.sync_headers and not self.headers_written:
                        return

                    if not self.video_header_written:
                        return
            elif isinstance(tag.data.data, VideoCommandFrame):
                return
            else:
                if self.sync_headers and not self.headers_written:
                    return

        elif isinstance(tag.data, ScriptData):
            if tag.data.name == "onMetaData":
                if self.duration:
                    tag.data.value["duration"] = self.duration
                elif "duration" in tag.data.value:
                    del tag.data.value["duration"]
            else:
                return False

        return True

    def adjust_tag_gap(self, tag):
        timestamp_gap = tag.timestamp - self.timestamps_orig.get(tag.type, 0)
        timestamp_sub = self.timestamps_sub.get(tag.type)
        if timestamp_gap > 1000 and timestamp_sub is not None:
            self.timestamps_sub[tag.type] += timestamp_gap

        self.timestamps_orig[tag.type] = tag.timestamp

    def adjust_tag_timestamp(self, tag):
        timestamp_offset_sub = self.timestamps_sub.get(tag.type)
        if timestamp_offset_sub is None and tag not in self.tags:
            self.timestamps_sub[tag.type] = tag.timestamp
            timestamp_offset_sub = self.timestamps_sub.get(tag.type)

        timestamp_offset_add = self.timestamps_add.get(tag.type)

        if timestamp_offset_add:
            tag.timestamp = max(0, tag.timestamp + timestamp_offset_add)
        elif timestamp_offset_sub:
            tag.timestamp = max(0, tag.timestamp - timestamp_offset_sub)

    def analyze_tags(self, tag_iterator):
        tags = list(islice(tag_iterator, 10))
        audio_tags = len(list(filter(lambda t: t.type == TAG_TYPE_AUDIO, tags)))
        video_tags = len(list(filter(lambda t: t.type == TAG_TYPE_VIDEO, tags)))

        self.has_audio = audio_tags > 0
        self.has_video = video_tags > 0

        if not (self.has_audio and self.has_video):
            self.sync_headers = False

        return tags

    def iter_tags(self, fd=None, buf=None, skip_header=None):
        if skip_header is None:
            skip_header = not not self.tags

        tags_iterator = filter(None, self.tags)
        flv_iterator = iter_flv_tags(fd=fd, buf=buf, skip_header=skip_header)

        yield from chain(tags_iterator, flv_iterator)

    def iter_chunks(self, fd=None, buf=None, skip_header=None):
        """Reads FLV tags from fd or buf and returns them with adjusted
           timestamps."""
        timestamps = dict(self.timestamps_add)
        tag_iterator = self.iter_tags(fd=fd, buf=buf, skip_header=skip_header)

        if not self.flv_header_written:
            analyzed_tags = self.analyze_tags(tag_iterator)
        else:
            analyzed_tags = []

        for tag in chain(analyzed_tags, tag_iterator):
            if not self.flv_header_written:
                flv_header = Header(has_video=self.has_video,
                                    has_audio=self.has_audio)
                yield flv_header.serialize()
                self.flv_header_written = True

            if self.verify_tag(tag):
                self.adjust_tag_gap(tag)
                self.adjust_tag_timestamp(tag)

                if self.duration:
                    norm_timestamp = tag.timestamp / 1000
                    if norm_timestamp > self.duration:
                        break
                yield tag.serialize()
                timestamps[tag.type] = tag.timestamp

        if not self.flatten_timestamps:
            self.timestamps_add = timestamps

        self.tags = []


class FLVTagConcatWorker(Thread):
    def __init__(self, iterator, stream):
        self.error = None
        self.stream = stream
        self.stream_iterator = iterator
        self.concater = FLVTagConcat(stream.duration, stream.tags,
                                     **stream.concater_params)

        Thread.__init__(self)
        self.daemon = True

    def run(self):
        for fd in self.stream_iterator:
            try:
                chunks = self.concater.iter_chunks(
                    fd, skip_header=self.stream.skip_header
                )
                for chunk in chunks:
                    self.stream.buffer.write(chunk)

                    if not self.running:
                        return
            except OSError as err:
                self.error = err
                break

        self.stop()

    def stop(self):
        self.running = False
        self.stream.buffer.close()

    def start(self):
        self.running = True
        return Thread.start(self)


class FLVTagConcatIO(IOBase):
    __worker__ = FLVTagConcatWorker

    def __init__(self, session, duration=None, tags=[], skip_header=None,
                 timeout=30, **concater_params):
        self.session = session
        self.timeout = timeout

        self.concater_params = concater_params
        self.duration = duration
        self.skip_header = skip_header
        self.tags = tags

    def open(self, iterator):
        self.buffer = RingBuffer(self.session.get_option("ringbuffer-size"))
        self.worker = self.__worker__(iterator, self)
        self.worker.start()

    def close(self):
        self.worker.stop()

        if self.worker.is_alive():
            self.worker.join()

    def read(self, size=-1):
        if not self.buffer:
            return b""

        if self.worker.error:
            raise self.worker.error

        return self.buffer.read(size, block=self.worker.is_alive(),
                                timeout=self.timeout)
