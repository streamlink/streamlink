from __future__ import division

from collections import namedtuple
from io import IOBase
from itertools import chain
from threading import Thread

from ..buffers import RingBuffer
from ..packages.flashmedia import FLVError
from ..packages.flashmedia.tag import (AudioData, AACAudioData, VideoData,
                                       AVCVideoData, VideoCommandFrame,
                                       Header, ScriptData, Tag)


__all__ = ["extract_flv_header_tags", "FLVTagConcat", "FLVTagConcatIO"]

AAC_SEQUENCE_HEADER = 0x00
AVC_SEQUENCE_HEADER = 0x00
AVC_SEQUENCE_END = 0x02

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
        except (IOError, FLVError) as err:
            if "Insufficient tag header" in str(err):
                break

            raise IOError(err)

        yield tag


def extract_flv_header_tags(stream):
    fd = stream.open()
    metadata = aac_header = avc_header = None

    for tag_index, tag in enumerate(iter_flv_tags(fd)):
        if isinstance(tag.data, ScriptData) and tag.data.name == "onMetaData":
            metadata = tag
        elif (isinstance(tag.data, VideoData) and
              isinstance(tag.data.data, AVCVideoData)):
            if tag.data.data.type == AVC_SEQUENCE_HEADER:
                avc_header = tag
        elif (isinstance(tag.data, AudioData) and
              isinstance(tag.data.data, AACAudioData)):
            if tag.data.data.type == AAC_SEQUENCE_HEADER:
                aac_header = tag

        if aac_header and avc_header and metadata:
            break

        # Give up after 10 tags
        if tag_index == 9:
            break

    return FLVHeaderTags(metadata, aac_header, avc_header)


class FLVTagConcat(object):
    def __init__(self, duration=None, tags=[], has_video=True, has_audio=True,
                 flatten_timestamps=False):
        self.duration = duration
        self.flatten_timestamps = flatten_timestamps
        self.has_audio = has_audio
        self.has_video = has_video
        self.tags = tags

        self.avc_header_written = False
        self.aac_header_written = False
        self.flv_header_written = False
        self.timestamps_add = {}
        self.timestamps_sub = {}

    def verify_tag(self, tag):
        if tag.filter:
            raise IOError("Tag has filter flag set, probably encrypted")

        if isinstance(tag.data, AudioData):
            if isinstance(tag.data.data, AACAudioData):
                if tag.data.data.type == AAC_SEQUENCE_HEADER:
                    if self.aac_header_written:
                        return

                    self.aac_header_written = True
                else:
                    if not self.aac_header_written:
                        return

        elif isinstance(tag.data, VideoData):
            if isinstance(tag.data.data, AVCVideoData):
                if tag.data.data.type == AVC_SEQUENCE_HEADER:
                    if self.avc_header_written:
                        return

                    self.avc_header_written = True
                else:
                    if not self.avc_header_written:
                        return

            elif isinstance(tag.data.data, VideoCommandFrame):
                return

        elif isinstance(tag.data, ScriptData):
            if tag.data.name == "onMetaData":
                if self.duration:
                    tag.data.value["duration"] = self.duration
                elif "duration" in tag.data.value:
                    del tag.data.value["duration"]

        return True

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

    def iter_tags(self, fd=None, buf=None, skip_header=None):
        if skip_header is None:
            skip_header = not not self.tags

        tags_iterator = filter(None, self.tags)
        flv_iterator = iter_flv_tags(fd=fd, buf=buf, skip_header=skip_header)

        for tag in chain(tags_iterator, flv_iterator):
            yield tag

    def iter_chunks(self, fd=None, buf=None, skip_header=None):
        """Reads FLV tags from fd or buf and returns them with adjusted
           timestamps."""
        timestamps = dict(self.timestamps_add)

        for tag in self.iter_tags(fd=fd, buf=buf, skip_header=skip_header):
            if not self.flv_header_written:
                flv_header = Header(has_video=self.has_video,
                                    has_audio=self.has_audio)
                yield flv_header.serialize()
                self.flv_header_written = True

            if self.verify_tag(tag):
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
        self.concater = FLVTagConcat(stream.duration, stream.tags)

        Thread.__init__(self)
        self.daemon = True

    def run(self):
        for fd in self.stream_iterator:
            try:
                for chunk in self.concater.iter_chunks(fd):
                    self.stream.buffer.write(chunk)

                    if not self.running:
                        return
            except IOError as err:
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
    __log_name__ = "stream.flv_concat"

    def __init__(self, session, duration=None, tags=[], timeout=30):
        self.session = session
        self.timeout = timeout
        self.logger = session.logger.new_module(self.__log_name__)

        self.duration = duration
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
            raise self.filler.error

        return self.buffer.read(size, block=self.worker.is_alive(),
                                timeout=self.timeout)
