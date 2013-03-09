from .stream import Stream
from ..compat import urljoin, urlparse, bytes, queue, range, is_py33
from ..exceptions import StreamError
from ..utils import absolute_url, urlget, res_xml, get_node_text, RingBuffer

from io import BytesIO, IOBase
from math import ceil
from threading import Lock, Thread, Timer
from time import time

import base64
import re
import requests
import os.path

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
    FragmentURL = "{url}{identifier}{quality}Seg{segment}-Frag{fragment}"

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
        url = absolute_url(self.baseurl, self.url)

        return self.FragmentURL.format(url=url, identifier=self.identifier,
                                       quality="", segment=segment,
                                       fragment=fragment)


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
        self.timestamp = bootstrap.payload.current_media_time
        self.identifier = bootstrap.payload.movie_identifier
        self.time_scale = float(bootstrap.payload.time_scale)
        self.segmentruntable = bootstrap.payload.segment_run_table_entries[0]
        self.fragmentruntable = bootstrap.payload.fragment_run_table_entries[0]

        max_fragments = self._fragment_count()
        fragment_duration = self._fragment_duration(max_fragments)

        if max_fragments != self.max_fragments:
            self.bootstrap_changed = True
            self.max_fragments = max_fragments
        else:
            self.bootstrap_changed = False

        if self.current_fragment < 0:
            if self.live:
                current_fragment = max_fragments

                # Less likely to hit edge if we don't start with last fragment,
                # default buffer is 10 sec.
                fragment_buffer = int(ceil(self.buffer_time / fragment_duration))
                current_fragment = max(1, current_fragment - (fragment_buffer - 1))

                self.logger.debug("Live edge buffer {0} sec is {1} fragments",
                                  self.buffer_time, fragment_buffer)
            else:
                current_fragment = 1

            self.current_fragment = current_fragment

        self.logger.debug("Current timestamp: {0}", self.timestamp / self.time_scale)
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

        self.bootstrap_changed = self.current_fragment != self.max_fragments

    def _fetch_bootstrap(self, url):
        res = urlget(url, exception=IOError)
        return Box.deserialize(BytesIO(res.content))

    def _segment_from_fragment(self, fragment):
        table = self.segmentruntable.payload.segment_run_entry_table
        segment = 1

        # For some reason servers seem to lie about the amount of fragments
        # per segment when there is only 1 segment run, so it's probably best
        # to only depend on that when there is multiple segment runs available
        # and return 1 otherwise.
        if len(table) > 1:
            prev_end = None

            for segmentrun in table:
                if prev_end is None:
                    end = (segmentrun.first_segment) * segmentrun.fragments_per_segment
                    start = (end - segmentrun.fragments_per_segment) + 1
                else:
                    start = prev_end + 1
                    end = (start + segmentrun.fragments_per_segment) - 1

                if fragment >= start:
                    segment = segmentrun.first_segment

                    # Calculate the correct segment offset incase there is a gap
                    # in the segment run table.
                    if fragment > end:
                        distance = fragment - end
                        offset = ceil(float(distance) / float(segmentrun.fragments_per_segment))
                        segment += offset

                prev_end = end

        return int(segment)

    def _debug_fragment_table(self):
        fragmentruntable = self.fragmentruntable.payload.fragment_run_entry_table

        for i, fragmentrun in enumerate(fragmentruntable):
            print(fragmentrun.first_fragment, fragmentrun.first_fragment_timestamp,
                  fragmentrun.fragment_duration, fragmentrun.discontinuity_indicator)

    def _fragment_count(self):
        segmentruntable = self.segmentruntable.payload.segment_run_entry_table

        if len(segmentruntable) > 1:
            return self._fragment_count_from_segment_table()
        else:
            return self._fragment_count_from_fragment_table()

    def _fragment_count_from_fragment_table(self):
        last_valid_fragmentrun = None
        table = self.fragmentruntable.payload.fragment_run_entry_table

        for i, fragmentrun in enumerate(table):
            if fragmentrun.discontinuity_indicator is not None:
                if fragmentrun.discontinuity_indicator == 0:
                    break
                elif fragmentrun.discontinuity_indicator > 0:
                    continue

            last_valid_fragmentrun = fragmentrun

        if last_valid_fragmentrun:
            return last_valid_fragmentrun.first_fragment
        else:
            return 0

    def _fragment_count_from_segment_table(self):
        last_frag = None
        table = self.segmentruntable.payload.segment_run_entry_table

        for segmentrun in table:
            if last_frag is None:
                end = (segmentrun.first_segment) * segmentrun.fragments_per_segment
                start = (end - segmentrun.fragments_per_segment) + 1
            else:
                start = last_frag + 1
                end = (start + segmentrun.fragments_per_segment) - 1

            last_frag = end

        return last_frag

    def _fragment_duration(self, fragment):
        fragment_duration = 0
        table = self.fragmentruntable.payload.fragment_run_entry_table
        time_scale = float(self.fragmentruntable.payload.time_scale)

        for i, fragmentrun in enumerate(table):
            if fragmentrun.discontinuity_indicator is not None:
                # Check for the last fragment of the stream
                if fragmentrun.discontinuity_indicator == 0:
                    if i > 0:
                        prev = table[i-1]
                        self.last_fragment = prev.first_fragment

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

        res = urlget(url, params=dict(hdcore="2.9.4"),
                     exception=IOError, session=rsession)

        bootstraps = {}
        streams = {}

        dom = res_xml(res, "manifest XML", exception=IOError)
        parsed = urlparse(url)
        baseurl = urljoin(url, os.path.dirname(parsed.path)) + "/"

        for baseurl in dom.getElementsByTagName("baseURL"):
            baseurl = get_node_text(baseurl)


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
            if media.hasAttribute("url") and media.hasAttribute("bootstrapInfoId"):
                bootstrapid = media.getAttribute("bootstrapInfoId")

                if not bootstrapid in bootstraps:
                    continue

                if media.hasAttribute("bitrate"):
                    quality = media.getAttribute("bitrate") + "k"
                elif media.hasAttribute("streamId"):
                    quality = media.getAttribute("streamId")
                else:
                    continue

                bootstrap = bootstraps[bootstrapid]
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

            elif media.hasAttribute("href"):
                href = media.getAttribute("href")
                url = absolute_url(baseurl, href)
                child_streams = cls.parse_manifest(session, url,
                                                   timeout=timeout,
                                                   rsession=rsession)

                for name, stream in child_streams.items():
                    # Override stream name if bitrate is available in parent
                    # manifest but not the child one.
                    if media.hasAttribute("bitrate") and not re.match("^(\d+)k$", name):
                        name = media.getAttribute("bitrate") + "k"

                    streams[name] = stream

        return streams
