from __future__ import division

import base64
import re
import requests
import os.path

from io import BytesIO, IOBase
from math import ceil
from threading import Thread, Timer
from time import time

from .stream import Stream
from ..buffers import RingBuffer
from ..compat import urljoin, urlparse, bytes, queue, range, is_py33
from ..exceptions import StreamError
from ..utils import absolute_url, urlget, res_xml

from ..packages.flashmedia import F4V, F4VError, FLVError
from ..packages.flashmedia.box import Box
from ..packages.flashmedia.tag import (AudioData, AACAudioData, VideoData,
                                       AVCVideoData, VideoCommandFrame,
                                       ScriptData, Header, Tag,
                                       TAG_TYPE_SCRIPT, TAG_TYPE_AUDIO,
                                       TAG_TYPE_VIDEO)

AAC_SEQUENCE_HEADER = 0x00
AVC_SEQUENCE_HEADER = 0x00
AVC_SEQUENCE_END = 0x02

# Some streams hosted by Akamai seems to require a hdcore parameter
# to function properly.
HDCORE_VERSION = "3.1.0"

class HDSStreamFiller(Thread):
    def __init__(self, stream):
        Thread.__init__(self)

        self.daemon = True
        self.error = None
        self.running = False
        self.stream = stream
        self.queue = queue.Queue(maxsize=5)

        self.avc_header_written = False
        self.aac_header_written = False

        self.timestamps = {
            TAG_TYPE_AUDIO: None,
            TAG_TYPE_VIDEO: None,
            TAG_TYPE_SCRIPT: None
        }

        self.create_tag_buffer(8182 * 8)

    def create_tag_buffer(self, size):
        if is_py33:
            self.tag_buffer = memoryview(bytearray(size))
        else:
            self.tag_buffer = bytearray(size)

    def download_fragment(self, segment, fragment):
        url = self.stream.fragment_url(segment, fragment)

        self.stream.logger.debug("[Fragment {0}-{1}] Opening URL: {2}",
                                 segment, fragment, url)

        retries = 3
        res = None

        while retries > 0 and self.running:
            try:
                res = urlget(url, stream=True, exception=IOError,
                             params=dict(hdcore=HDCORE_VERSION),
                             session=self.stream.rsession, timeout=10)
                break
            except IOError as err:
                self.stream.logger.error("[Fragment {0}-{1}] Failed to open: {2}",
                                         segment, fragment, str(err))

            retries -= 1

        if not res:
            return

        size = int(res.headers.get("content-length", "0"))
        size = size * self.stream.buffer_fragments

        if size > self.stream.buffer.buffer_size:
            self.stream.buffer.resize(size)

        return self.convert_fragment(segment, fragment, res.raw)

    def convert_fragment(self, segment, fragment, fd):
        mdat = None

        try:
            f4v = F4V(fd, raw_payload=True)

            # Fast forward to mdat box
            for box in f4v:
                if box.type == "mdat":
                    mdat = box.payload.data
                    break

        except F4VError as err:
            self.stream.logger.error("[Fragment {0}-{1}] Failed to deserialize: {2}",
                                     segment, fragment, str(err))
            return

        if not mdat:
            self.stream.logger.error("[Fragment {0}-{1}] No mdat box found",
                                     segment, fragment)
            return

        self.stream.logger.debug(("[Fragment {0}-{1}] Extracting FLV tags from"
                                  " MDAT box"), segment, fragment)

        mdat_size = len(mdat)

        if mdat_size > len(self.tag_buffer):
            self.create_tag_buffer(mdat_size)

        self.mdat_offset = 0
        self.tag_offset = 0

        while self.running and self.mdat_offset < mdat_size:
            try:
                self.extract_flv_tag(mdat)
            except (FLVError, IOError) as err:
                self.stream.logger.error(("Failed to extract FLV tag from MDAT"
                                          " box: {0}").format(str(err)))
                break

        self.stream.buffer.write(self.tag_buffer[:self.tag_offset])

        return True

    def extract_flv_tag(self, mdat):
        tag, self.mdat_offset = Tag.deserialize_from(mdat, self.mdat_offset)

        if tag.filter:
            self.stop()
            self.error = IOError("Tag has filter flag set, probably encrypted")
            raise self.error

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

        if isinstance(tag.data, VideoData):
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


        if tag.type in self.timestamps:
            if self.timestamps[tag.type] is None:
                self.timestamps[tag.type] = tag.timestamp
            else:
                tag.timestamp = max(0, tag.timestamp - self.timestamps[tag.type])

        self.tag_offset = tag.serialize_into(self.tag_buffer, self.tag_offset)

    def run(self):
        self.stream.logger.debug("Starting buffer filler thread")

        while self.running:
            try:
                segment, fragment, fragment_duration = self.queue.get(True, 5)
            except queue.Empty:
                continue

            # Make sure timestamps don't get out of sync when
            # a fragment is missing or failed to download.
            if not self.download_fragment(segment, fragment):
                for key, value in self.timestamps.items():
                    if value is not None:
                        self.timestamps[key] += fragment_duration
                    else:
                        self.timestamps[key] = fragment_duration

            if fragment == self.stream.end_fragment:
                break

        self.stop()
        self.stream.logger.debug("Buffer filler thread completed")

    def start(self):
        self.running = True

        return Thread.start(self)

    def stop(self):
        self.running = False
        self.stream.buffer.close()

        if self.stream.bootstrap_timer:
            self.stream.bootstrap_timer.cancel()


class HDSStreamIO(IOBase):
    FragmentURL = "{url}{identifier}{quality}Seg{segment}-Frag{fragment}"

    def __init__(self, session, baseurl, url, bootstrap, metadata=None,
                 timeout=60, rsession=None):

        self.buffer = None
        self.buffer_time = session.options.get("hds-live-edge")
        self.buffer_fragments = int(session.options.get("hds-fragment-buffer"))
        self.baseurl = baseurl
        self.bootstrap = bootstrap
        self.logger = session.logger.new_module("stream.hds")
        self.metadata = metadata
        self.session = session
        self.timeout = timeout
        self.url = url

        if rsession:
            self.rsession = rsession
        else:
            self.rsession = requests.session()

    def open(self):
        self.current_segment = -1
        self.current_fragment = -1
        self.first_fragment = 1
        self.last_fragment = -1
        self.end_fragment = None

        self.bootstrap_timer = None
        self.bootstrap_minimal_reload_time = 2.0
        self.bootstrap_reload_time = self.bootstrap_minimal_reload_time
        self.bootstrap_reload_timestamp = 0
        self.invalid_fragments = set()

        self.buffer = RingBuffer()
        self.header_written = False

        self.filler = HDSStreamFiller(self)
        self.filler.start()

        try:
            self.update_bootstrap(silent=False, fillqueue=True)
        except StreamError:
            self.close()
            raise

        return self

    def close(self):
        self.filler.stop()

        if self.filler.is_alive():
            self.filler.join()

    def read(self, size=-1):
        if not self.buffer:
            return b""

        if self.filler.error:
            raise self.filler.error

        return self.buffer.read(size, block=self.filler.is_alive(),
                                timeout=self.timeout)

    def fragment_url(self, segment, fragment):
        url = absolute_url(self.baseurl, self.url)

        return self.FragmentURL.format(url=url, identifier=self.identifier,
                                       quality="", segment=segment,
                                       fragment=fragment)


    def update_bootstrap(self, silent=True, fillqueue=False):
        if not self.filler.running:
            return

        if self.end_fragment and self.current_fragment > self.end_fragment:
            return

        # Wait until buffer has room before requesting a new bootstrap
        self.buffer.wait_free()

        elapsed = time() - self.bootstrap_reload_timestamp
        if elapsed > self.bootstrap_reload_time:
            try:
                self._update_bootstrap()
            except IOError as err:
                self.bootstrap_reload_time = self.bootstrap_minimal_reload_time

                if silent:
                    self.logger.error("Failed to update bootstrap: {0}",
                                      str(err))
                else:
                    raise StreamError(str(err))

        if not self.header_written:
            flvheader = Header(has_video=True, has_audio=True)
            self.buffer.write(flvheader.serialize())

            if self.metadata:
                # Remove duration from metadata when it's a livestream
                # since it will just confuse players anyway.
                if self.live and "duration" in self.metadata.value:
                    del self.metadata.value["duration"]

                tag = Tag(TAG_TYPE_SCRIPT, timestamp=0, data=self.metadata)
                self.buffer.write(tag.serialize())

            self.header_written = True

        if self.bootstrap_changed:
            self._queue_fragments(fillqueue)

        if self.bootstrap_timer:
            self.bootstrap_timer.cancel()

        self.bootstrap_timer = Timer(1, self.update_bootstrap)
        self.bootstrap_timer.daemon = True
        self.bootstrap_timer.start()

    def _update_bootstrap(self):
        self.logger.debug("Updating bootstrap")

        if isinstance(self.bootstrap, Box):
            bootstrap = self.bootstrap
        else:
            bootstrap = self._fetch_bootstrap(self.bootstrap)

        self.live = bootstrap.payload.live
        self.profile = bootstrap.payload.profile
        self.timestamp = bootstrap.payload.current_media_time
        self.identifier = bootstrap.payload.movie_identifier
        self.time_scale = bootstrap.payload.time_scale
        self.segmentruntable = bootstrap.payload.segment_run_table_entries[0]
        self.fragmentruntable = bootstrap.payload.fragment_run_table_entries[0]

        self.first_fragment, last_fragment = self._fragment_count()
        fragment_duration = self._fragment_duration(last_fragment)

        if last_fragment != self.last_fragment:
            self.bootstrap_changed = True
            self.last_fragment = last_fragment
        else:
            self.bootstrap_changed = False

        if self.current_fragment < 0:
            if self.live:
                current_fragment = last_fragment

                # Less likely to hit edge if we don't start with last fragment,
                # default buffer is 10 sec.
                fragment_buffer = int(ceil(self.buffer_time / fragment_duration))
                current_fragment = max(self.first_fragment, current_fragment - (fragment_buffer - 1))

                self.logger.debug("Live edge buffer {0} sec is {1} fragments",
                                  self.buffer_time, fragment_buffer)
            else:
                current_fragment = self.first_fragment

            self.current_fragment = current_fragment

        self.logger.debug("Current timestamp: {0}", self.timestamp / self.time_scale)
        self.logger.debug("Current segment: {0}", self.current_segment)
        self.logger.debug("Current fragment: {0}", self.current_fragment)
        self.logger.debug("First fragment: {0}", self.first_fragment)
        self.logger.debug("Last fragment: {0}", self.last_fragment)
        self.logger.debug("End fragment: {0}", self.end_fragment)

        self.bootstrap_reload_timestamp = time()
        self.bootstrap_reload_time = fragment_duration

        if self.live and not self.bootstrap_changed:
            self.logger.debug("Bootstrap not changed, shortening timer")
            self.bootstrap_reload_time /= 2

        if self.bootstrap_reload_time < self.bootstrap_minimal_reload_time:
            self.bootstrap_reload_time = self.bootstrap_minimal_reload_time

    def _queue_fragments(self, fillqueue=False):
        for i, fragment in enumerate(range(self.current_fragment, self.last_fragment + 1)):
            if not self.filler.running or (fillqueue and i == self.filler.queue.maxsize):
                break

            if fragment in self.invalid_fragments:
                continue

            self.current_fragment = fragment + 1
            self.current_segment = self._segment_from_fragment(fragment)
            fragment_duration = int(self._fragment_duration(fragment) * 1000)
            entry = (self.current_segment, fragment, fragment_duration)

            self.logger.debug("[Fragment {0}-{1}] Adding to queue",
                               entry[0], entry[1])

            while self.filler.running:
                try:
                    self.filler.queue.put(entry, True, 5)
                    break
                except queue.Full:
                    continue

        self.bootstrap_changed = self.current_fragment != self.last_fragment

    def _fetch_bootstrap(self, url):
        res = urlget(url, params=dict(hdcore=HDCORE_VERSION),
                     exception=IOError)
        return Box.deserialize(BytesIO(res.content))

    def _segment_from_fragment(self, fragment):
        table = self.segmentruntable.payload.segment_run_entry_table

        for segment, start, end in self._iterate_segments(table):
            if fragment >= start and fragment <= end:
                break
        else:
            segment = 1

        return segment

    def _iterate_segments(self, table):
        # If the first segment in the table starts at the beginning we can go from there,
        # otherwise we start from the end and use the total fragment count to figure
        # out where the last segment ends.

        if table[0].first_segment == 1:
            prev_frag = self.first_fragment - 1

            for segmentrun in table:
                start = prev_frag + 1
                end = prev_frag + segmentrun.fragments_per_segment

                yield segmentrun.first_segment, start, end

                prev_frag = end
        else:
            prev_frag = self.last_fragment + 1

            for segmentrun in reversed(table):
                start = prev_frag - segmentrun.fragments_per_segment
                end = prev_frag - 1

                yield segmentrun.first_segment, start, end

                prev_frag = start

    def _debug_fragment_table(self):
        fragmentruntable = self.fragmentruntable.payload.fragment_run_entry_table

        for i, fragmentrun in enumerate(fragmentruntable):
            print(fragmentrun.first_fragment, fragmentrun.first_fragment_timestamp,
                  fragmentrun.fragment_duration, fragmentrun.discontinuity_indicator)

    def _fragment_count(self):
        table = self.fragmentruntable.payload.fragment_run_entry_table
        first_fragment, end_fragment = None, None

        for i, fragmentrun in enumerate(table):
            if fragmentrun.discontinuity_indicator is not None:
                if fragmentrun.discontinuity_indicator == 0:
                    break
                elif fragmentrun.discontinuity_indicator > 0:
                    continue

            if first_fragment is None:
                first_fragment = fragmentrun.first_fragment

            end_fragment = fragmentrun.first_fragment
            fragment_duration = fragmentrun.first_fragment_timestamp + fragmentrun.fragment_duration

            if self.timestamp > fragment_duration:
                offset = (self.timestamp - fragment_duration) / fragmentrun.fragment_duration
                end_fragment += int(offset)

        if first_fragment is None:
            first_fragment = 1

        if end_fragment is None:
            end_fragment = 1

        return first_fragment, end_fragment

    def _fragment_duration(self, fragment):
        fragment_duration = 0
        table = self.fragmentruntable.payload.fragment_run_entry_table
        time_scale = self.fragmentruntable.payload.time_scale

        for i, fragmentrun in enumerate(table):
            if fragmentrun.discontinuity_indicator is not None:
                self.invalid_fragments.add(fragmentrun.first_fragment)

                # Check for the last fragment of the stream
                if fragmentrun.discontinuity_indicator == 0:
                    if i > 0:
                        prev = table[i-1]
                        self.end_fragment = prev.first_fragment

                    break
                elif fragmentrun.discontinuity_indicator > 0:
                    continue

            if fragment >= fragmentrun.first_fragment:
                fragment_duration = fragmentrun.fragment_duration / time_scale

        return fragment_duration


class HDSStream(Stream):
    """
    Implements the Adobe HTTP Dynamic Streaming protocol

    *Attributes:*

    - :attr:`baseurl` Base URL
    - :attr:`url` Base path of the stream, joined with the base URL when fetching fragments
    - :attr:`bootstrap` Either a URL pointing to the bootstrap or a bootstrap :class:`Box` object
      used for initial information about the stream
    - :attr:`metadata` Either `None` or a :class:`ScriptData` object that contains metadata about
      the stream, such as height, width and bitrate
    """

    __shortname__ = "hds"

    def __init__(self, session, baseurl, url, bootstrap, metadata=None,
                 timeout=60, rsession=None):
        Stream.__init__(self, session)

        self.baseurl = baseurl
        self.url = url
        self.bootstrap = bootstrap
        self.metadata = metadata
        self.timeout = timeout
        self.rsession = rsession

    def __repr__(self):
        return ("<HDSStream({0!r}, {1!r}, {2!r},"
                " metadata={3!r}, timeout={4!r})>").format(self.baseurl,
                                                           self.url,
                                                           self.bootstrap,
                                                           self.metadata,
                                                           self.timeout)

    def __json__(self):
        if isinstance(self.bootstrap, Box):
            bootstrap = base64.b64encode(self.bootstrap.serialize())
        else:
            bootstrap = self.bootstrap

        if isinstance(self.metadata, ScriptData):
            metadata = self.metadata.__dict__
        else:
            metadata = self.metadata

        return dict(type=HDSStream.shortname(), baseurl=self.baseurl,
                    url=self.url, bootstrap=bootstrap, metadata=metadata)

    def open(self):
        fd = HDSStreamIO(self.session, self.baseurl, self.url, self.bootstrap,
                         self.metadata, self.timeout, self.rsession)

        return fd.open()

    @classmethod
    def parse_manifest(cls, session, url, timeout=60, rsession=None):
        if not rsession:
            rsession = requests.session()

        res = urlget(url, params=dict(hdcore=HDCORE_VERSION),
                     exception=IOError, session=rsession)
        manifest = res_xml(res, "manifest XML", ignore_ns=True,
                           exception=IOError)

        parsed = urlparse(url)
        baseurl = manifest.findtext("baseURL")
        bootstraps = {}
        streams = {}

        if not baseurl:
            baseurl = urljoin(url, os.path.dirname(parsed.path)) + "/"

        for bootstrap in manifest.findall("bootstrapInfo"):
            name = bootstrap.attrib.get("id") or "_global"
            url = bootstrap.attrib.get("url")

            if url:
                box = absolute_url(baseurl, url)
            else:
                data = base64.b64decode(bytes(bootstrap.text, "utf8"))
                box = Box.deserialize(BytesIO(data))

            bootstraps[name] = box

        for media in manifest.findall("media"):
            url = media.attrib.get("url")
            bootstrapid = media.attrib.get("bootstrapInfoId", "_global")
            href = media.attrib.get("href")

            if url and bootstrapid:
                bootstrap = bootstraps.get(bootstrapid)

                if not bootstrap:
                    continue

                bitrate = media.attrib.get("bitrate")
                streamid = media.attrib.get("streamId")

                if bitrate:
                    quality = bitrate + "k"
                elif streamid:
                    quality = streamid
                else:
                    continue

                metadata = media.findtext("metadata")

                if metadata:
                    metadata = base64.b64decode(bytes(metadata, "utf8"))
                    metadata = ScriptData.deserialize(BytesIO(metadata))
                else:
                    metadata = None

                stream = HDSStream(session, baseurl, url, bootstrap,
                                   metadata=metadata, timeout=timeout,
                                   rsession=rsession)
                streams[quality] = stream

            elif href:
                url = absolute_url(baseurl, href)
                child_streams = cls.parse_manifest(session, url,
                                                   timeout=timeout,
                                                   rsession=rsession)

                for name, stream in child_streams.items():
                    # Override stream name if bitrate is available in parent
                    # manifest but not the child one.
                    bitrate = media.attrib.get("bitrate")

                    if bitrate and not re.match("^(\d+)k$", name):
                        name = bitrate + "k"

                    streams[name] = stream

        return streams
