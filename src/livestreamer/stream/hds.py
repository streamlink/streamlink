from . import Stream, StreamError
from ..compat import urljoin, urlparse, bytes, queue, range
from ..utils import absolute_url, urlget, res_xml, get_node_text, RingBuffer

from io import BytesIO, IOBase
from math import ceil, floor
from threading import Lock, Thread, Timer
from time import sleep, time

import base64
import requests
import os.path
import xml.dom.minidom

from ..packages.flashmedia import F4VError
from ..packages.flashmedia.box import Box
from ..packages.flashmedia.f4v import F4V
from ..packages.flashmedia.packet import Packet
from ..packages.flashmedia.tag import (AudioData, AACAudioData, VideoData,
                                       AVCVideoData, VideoCommandFrame,
                                       ScriptData, Header, Tag, TagDataTypes,
                                       RawData, TAG_TYPE_SCRIPT,
                                       TAG_TYPE_AUDIO, TAG_TYPE_VIDEO)


AAC_SEQUENCE_HEADER = 0x00
AVC_SEQUENCE_HEADER = 0x00
AVC_SEQUENCE_END = 0x02


class Frame(Packet):
    def __init__(self, type, size, timestamp, data):
        self.type = type
        self.size = size
        self.timestamp = timestamp
        self.data = data

    @classmethod
    def _deserialize(cls, io):
        type_ = io.read_u8()
        size = io.read_u24()
        timestamp = io.read_s32e()
        n = io.read_u24()

        io.data_left = size

        if type_ in TagDataTypes:
            data = TagDataTypes[type_].deserialize(io=io)
        else:
            data = io.read(size)
            data = RawData(data)

        io.data_left = None
        last_tag_size = io.read_u32()

        return cls(type_, size, timestamp, data)


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
            AudioData: None,
            ScriptData: None,
            VideoData: None
        }

    def download_fragment(self, segment, fragment):
        url = self.stream.fragment_url(segment, fragment)

        self.stream.logger.debug("[Fragment {0}-{1}] Opening URL: {2}",
                                 segment, fragment, url)

        retries = 3
        res = None

        while retries > 0 and self.running:
            try:
                res = urlget(url, stream=True, exception=IOError,
                             session=self.stream.rsession, timeout=10)
                break
            except IOError as err:
                self.stream.logger.error("[Fragment {0}-{1}] Failed to open: {2}",
                                         segment, fragment, str(err))

            retries -= 1

        if not res:
            return

        fd = None

        size = int(res.headers.get("content-length", "0"))
        size = size * self.stream.buffer_fragments

        if size > self.stream.buffer.buffer_size:
            self.stream.buffer.resize(size)

        try:
            f4v = F4V(res.raw, preload=False)

            # Fast forward to mdat box
            for box in f4v:
                if box.type == "mdat":
                    fd = box.payload
                    break

        except F4VError as err:
            self.stream.logger.error("[Fragment {0}-{1}] Failed to parse: {2}",
                                     segment, fragment, str(err))
            return

        if not fd:
            self.stream.logger.error("[Fragment {0}-{1}] No mdat box found",
                                     segment, fragment)
            return

        self.stream.logger.debug(("[Fragment {0}-{1}] Converting mdat box "
                                  "to FLV tags"), segment, fragment)

        while self.running:
            try:
                self.add_flv_tag(fd)
            except Exception as err:
                break

        self.stream.logger.debug("[Fragment {0}-{1}] Download complete", segment,
                                 fragment)

    def add_flv_tag(self, fd):
        frame = Frame.deserialize(fd)

        if isinstance(frame.data, RawData):
            self.stop()
            self.error = IOError("Unhandled frame, probably encrypted")
            raise self.error

        if isinstance(frame.data, AudioData):
            if isinstance(frame.data.data, AACAudioData):
                if frame.data.data.type == AAC_SEQUENCE_HEADER:
                    if self.aac_header_written:
                        return

                    self.aac_header_written = True
                else:
                    if not self.aac_header_written:
                        return self.stream.logger.debug("Skipping AAC data before header")

        if isinstance(frame.data, VideoData):
            if isinstance(frame.data.data, AVCVideoData):
                if frame.data.data.type == AVC_SEQUENCE_HEADER:
                    if self.avc_header_written:
                        return

                    self.avc_header_written = True
                else:
                    if not self.avc_header_written:
                        return self.stream.logger.debug("Skipping AVC data before header")

            elif isinstance(frame.data.data, VideoCommandFrame):
                return self.stream.logger.debug("Skipping video command frame")

        tag = Tag(frame.type, timestamp=frame.timestamp,
                  data=frame.data)

        if type(frame.data) in self.timestamps:
            if self.timestamps[type(frame.data)] is None:
                self.timestamps[type(frame.data)] = frame.timestamp
            else:
                tag.timestamp = max(0, tag.timestamp - self.timestamps[type(frame.data)])

        data = tag.serialize()
        self.stream.buffer.write(data)

    def run(self):
        self.stream.logger.debug("Starting buffer filler thread")

        while self.running:
            try:
                segment, fragment = self.queue.get(True, 5)
            except queue.Empty:
                continue

            self.download_fragment(segment, fragment)

            if fragment == self.stream.last_fragment:
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
    FragmentURL = "{baseurl}{url}{identifier}{quality}Seg{segment}-Frag{fragment}"

    def __init__(self, session, baseurl, url, bootstrap, metadata=None,
                 timeout=60, rsession=None):

        self.buffer = None
        self.buffer_time = float(session.options.get("hds-live-edge"))
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
            self.rsession = requests.session(prefetch=False)

    def open(self):
        self.current_segment = -1
        self.current_fragment = -1
        self.last_fragment = None
        self.max_fragments = -1
        self.bootstrap_lock = Lock()
        self.bootstrap_timer = None
        self.bootstrap_minimal_reload_time = 2.0
        self.bootstrap_reload_time = self.bootstrap_minimal_reload_time
        self.bootstrap_reload_timestamp = 0

        self.buffer = RingBuffer()

        flvheader = Header(has_video=True, has_audio=True)
        self.buffer.write(flvheader.serialize())

        if self.metadata:
            tag = Tag(TAG_TYPE_SCRIPT, timestamp=0, data=self.metadata)
            self.buffer.write(tag.serialize())

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
        return self.FragmentURL.format(baseurl=self.baseurl, url=self.url,
                                       identifier=self.identifier, quality="",
                                       segment=segment, fragment=fragment)

    def update_bootstrap(self, silent=True, fillqueue=False):
        if not self.filler.running:
            return

        if self.last_fragment and self.current_fragment > self.last_fragment:
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
        self.timestamp = (bootstrap.payload.current_media_time / bootstrap.payload.time_scale) - 1
        self.identifier = bootstrap.payload.movie_identifier

        self.segmentruntable = bootstrap.payload.segment_run_table_entries[0]
        self.fragmentruntable = bootstrap.payload.fragment_run_table_entries[0]

        max_fragments, fragment_duration = self._fragment_from_timestamp(self.timestamp)

        if max_fragments != self.max_fragments:
            self.bootstrap_changed = True
            self.max_fragments = max_fragments
        else:
            self.bootstrap_changed = False

        if self.current_fragment < 0:
            if self.live:
                self.logger.debug("Current timestamp: {0}", self.timestamp)
                current_fragment, fragment_duration = self._fragment_from_timestamp(self.timestamp)

                fragment_buffer = int(ceil(self.buffer_time / fragment_duration))

                # Less likely to hit edge if we don't start with last fragment
                self.logger.debug("Fragment buffer {0} sec is {1} fragments",
                                  self.buffer_time, fragment_buffer)

                if current_fragment > fragment_buffer and fragment_buffer > 0:
                    current_fragment -= (fragment_buffer - 1)
            else:
                current_fragment, fragment_duration = self._fragment_from_timestamp(0)

            self.current_fragment = current_fragment

        self.logger.debug("Current segment: {0}", self.current_segment)
        self.logger.debug("Current fragment: {0}", self.current_fragment)
        self.logger.debug("Max fragments: {0}", self.max_fragments)
        self.logger.debug("Last fragment: {0}", self.last_fragment)

        self.bootstrap_reload_timestamp = time()
        self.bootstrap_reload_time = fragment_duration

        if self.live and not self.bootstrap_changed:
            self.logger.debug("Bootstrap not changed, shortening timer")
            self.bootstrap_reload_time /= 2

        if self.bootstrap_reload_time < self.bootstrap_minimal_reload_time:
            self.bootstrap_reload_time = self.bootstrap_minimal_reload_time

    def _queue_fragments(self, fillqueue=False):
        for i, fragment in enumerate(range(self.current_fragment, self.max_fragments + 1)):
            if not self.filler.running or (fillqueue and i == self.filler.queue.maxsize):
                break

            self.current_fragment = fragment + 1
            self.current_segment = self._segment_from_fragment(i)

            self.logger.debug("[Fragment {0}-{1}] Adding to queue",
                               self.current_segment, fragment)

            entry = (self.current_segment, fragment)

            while self.filler.running:
                try:
                    self.filler.queue.put(entry, True, 5)
                    break
                except queue.Full:
                    continue

        self.bootstrap_changed = self.current_fragment != self.max_fragments

    def _fetch_bootstrap(self, url):
        res = urlget(url, exception=IOError)
        return Box.deserialize(BytesIO(res.content))

    def _segment_from_fragment(self, fragment):
        if len(self.segmentruntable.payload.segment_run_entry_table) > 1:
            for segment, segment_start, segment_end in self._segment_fragment_pairs():
                if fragment >= segment_start and fragment <= segment_end:
                    return segment
        else:
            return 1

    def _segment_fragment_pairs(self):
        segmentruntable = self.segmentruntable.payload.segment_run_entry_table

        for segmentrun in segmentruntable:
            start = ((segmentrun.first_segment - 1) * segmentrun.fragments_per_segment)
            end = start + segmentrun.fragments_per_segment

            yield segmentrun.first_segment, start + 1, end

    def _debug_fragment_table(self):
        fragmentruntable = self.fragmentruntable.payload.fragment_run_entry_table
        time_scale = self.fragmentruntable.payload.time_scale

        prev_fragmentrun = None
        iterator = enumerate(fragmentruntable)
        for i, fragmentrun in iterator:
            print(fragmentrun.first_fragment, fragmentrun.first_fragment_timestamp,
                  fragmentrun.fragment_duration, fragmentrun.discontinuity_indicator)

    def _fragment_from_timestamp(self, timestamp):
        fragmentruntable = self.fragmentruntable.payload.fragment_run_entry_table
        time_scale = self.fragmentruntable.payload.time_scale

        fragment = 0
        for i, fragmentrun in enumerate(fragmentruntable):
            if fragmentrun.discontinuity_indicator is not None:
                if fragmentrun.discontinuity_indicator == 0:
                    prev = fragmentruntable[i-1]
                    self.last_fragment = prev.first_fragment
                    break
                elif fragmentrun.discontinuity_indicator > 0:
                    continue

            ftimestamp = fragmentrun.first_fragment_timestamp / time_scale
            fduration = fragmentrun.fragment_duration / time_scale

            if timestamp >= ftimestamp:
                offset = floor((timestamp - ftimestamp) / fduration)
                fragment = int(fragmentrun.first_fragment + offset)

        return (fragment, fduration)


class HDSStream(Stream):
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
    def parse_manifest(cls, session, url, timeout=60):
        rsession = requests.session()
        res = urlget(url, params=dict(hdcore="2.9.4"),
                     exception=IOError, session=rsession)

        bootstraps = {}
        streams = {}

        dom = res_xml(res, "manifest XML", exception=IOError)
        parsed = urlparse(url)
        baseurl = urljoin(url, os.path.dirname(parsed.path)) + "/"

        for baseurl in dom.getElementsByTagName("baseURL"):
            pass

        for bootstrap in dom.getElementsByTagName("bootstrapInfo"):
            if not bootstrap.hasAttribute("id"):
                continue

            name = bootstrap.getAttribute("id")

            if bootstrap.hasAttribute("url"):
                box = absolute_url(baseurl, bootstrap.getAttribute("url"))
            else:
                data = get_node_text(bootstrap)
                data = base64.b64decode(bytes(data, "utf8"))
                box = Box.deserialize(BytesIO(data))

            bootstraps[name] = box

        for media in dom.getElementsByTagName("media"):
            if not (media.hasAttribute("bitrate") and media.hasAttribute("url")
                    and media.hasAttribute("bootstrapInfoId")):
                continue

            bootstrapid = media.getAttribute("bootstrapInfoId")

            if not bootstrapid in bootstraps:
                continue

            bootstrap = bootstraps[bootstrapid]
            quality = media.getAttribute("bitrate") + "k"
            url = media.getAttribute("url")
            metadatas = media.getElementsByTagName("metadata")

            if len(metadatas) > 0:
                metadata = media.getElementsByTagName("metadata")[0]
                metadata = get_node_text(metadata)
                metadata = base64.b64decode(bytes(metadata, "utf8"))
                metadata = ScriptData.deserialize(BytesIO(metadata))
            else:
                metadata = None

            stream = HDSStream(session, baseurl, url, bootstrap,
                               metadata=metadata, timeout=timeout,
                               rsession=rsession)
            streams[quality] = stream

        return streams
