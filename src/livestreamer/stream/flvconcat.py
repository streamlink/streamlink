from collections import namedtuple
from io import IOBase
from itertools import chain
from threading import Thread

from ..buffers import RingBuffer
from ..packages.flashmedia import FLVError
from ..packages.flashmedia.tag import (AudioData, AACAudioData, VideoData,
                                       AVCVideoData, VideoCommandFrame,
                                       Header, ScriptData, Tag)


__all__ = ["extract_flv_header_tags", "FLVTagConcatIO"]

AAC_SEQUENCE_HEADER = 0x00
AVC_SEQUENCE_HEADER = 0x00
AVC_SEQUENCE_END = 0x02

FLVHeaderTags = namedtuple("FLVHeaderTags", ["metadata", "aac", "avc"])


def iterate_flv(fd, strict=False, skip_header=False):
    if not skip_header:
        Header.deserialize(fd)

    while True:
        try:
            tag = Tag.deserialize(fd, strict=strict)
        except (IOError, FLVError):
            break

        yield tag


def extract_flv_header_tags(stream):
    fd = stream.open()
    metadata = aac_header = avc_header = None

    for tag_index, tag in enumerate(iterate_flv(fd)):
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


class FLVTagConcatWorker(Thread):
    def __init__(self, iterator, stream):
        Thread.__init__(self)

        self.daemon = True

        self.avc_header_written = False
        self.aac_header_written = False
        self.flv_header_written = False

        self.timestamps_add = {}
        self.timestamps_sub = {}

        self.error = None
        self.stream = stream
        self.stream_iterator = iterator

    def verify_tag(self, tag):
        if tag.filter:
            self.stop()
            self.error = IOError("Tag has filter flag set, probably encrypted")
            return

        if isinstance(tag.data, AudioData):
            if isinstance(tag.data.data, AACAudioData):
                if tag.data.data.type == AAC_SEQUENCE_HEADER:
                    if self.aac_header_written:
                        return

                    self.aac_header_written = True
                else:
                    if not self.aac_header_written:
                        self.stream.logger.debug("Skipping AAC data before header")
                        return

        elif isinstance(tag.data, VideoData):
            if isinstance(tag.data.data, AVCVideoData):
                if tag.data.data.type == AVC_SEQUENCE_HEADER:
                    if self.avc_header_written:
                        return

                    self.avc_header_written = True
                else:
                    if not self.avc_header_written:
                        self.stream.logger.debug("Skipping AVC data before header")
                        return

            elif isinstance(tag.data.data, VideoCommandFrame):
                self.stream.logger.debug("Skipping video command frame")
                return

        elif isinstance(tag.data, ScriptData):
            if tag.data.name == "onMetaData":
                if self.stream.duration:
                    tag.data.value["duration"] = self.stream.duration
                elif "duration" in tag.data.value:
                    del tag.data.value["duration"]

        return True

    def adjust_tag_timestamp(self, tag):
        timestamp_offset_sub = self.timestamps_sub.get(tag.type)
        if timestamp_offset_sub is None and tag not in self.stream.tags:
            self.timestamps_sub[tag.type] = tag.timestamp
            timestamp_offset_sub = self.timestamps_sub.get(tag.type)

        timestamp_offset_add = self.timestamps_add.get(tag.type)

        if timestamp_offset_add:
            tag.timestamp = max(0, tag.timestamp + timestamp_offset_add)
        elif timestamp_offset_sub:
            tag.timestamp = max(0, tag.timestamp - timestamp_offset_sub)

    def iterate_tags(self, fd):
        tags_iterator = filter(None, self.stream.tags)
        flv_iterator = iterate_flv(fd, skip_header=not not self.stream.tags)

        for tag in chain(tags_iterator, flv_iterator):
            yield tag

    def write_tag(self, tag):
        self.stream.buffer.write(tag.serialize())

    def run(self):
        for fd in self.stream_iterator:
            timestamps = dict(self.timestamps_add)

            for tag in self.iterate_tags(fd):
                if not self.running:
                    return self.stop()

                if not self.flv_header_written:
                    flv_header = Header(has_video=True, has_audio=True)
                    self.write_tag(flv_header)
                    self.flv_header_written = True

                if self.verify_tag(tag):
                    self.adjust_tag_timestamp(tag)

                    if self.stream.duration:
                        norm_timestamp = tag.timestamp / 1000
                        if norm_timestamp > self.stream.duration:
                            return self.stop()

                    self.write_tag(tag)
                    timestamps[tag.type] = tag.timestamp

            self.timestamps_add = timestamps
            self.stream.tags = []

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

    def __init__(self, session, duration=None, tags=None, timeout=30):
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
