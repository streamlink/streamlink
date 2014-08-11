from __future__ import division

import base64
import hmac
import re
import os.path

from binascii import unhexlify
from collections import namedtuple
from hashlib import sha256
from io import BytesIO
from math import ceil

from .flvconcat import FLVTagConcat
from .segmented import (SegmentedStreamReader,
                        SegmentedStreamWriter,
                        SegmentedStreamWorker)
from .stream import Stream
from .wrappers import StreamIOIterWrapper

from ..cache import Cache
from ..compat import parse_qsl, urljoin, urlparse, bytes, range
from ..exceptions import StreamError
from ..utils import absolute_url, swfdecompress

from ..packages.flashmedia import F4V, F4VError
from ..packages.flashmedia.box import Box
from ..packages.flashmedia.tag import ScriptData, Tag, TAG_TYPE_SCRIPT

# Akamai HD player verification key
# Use unhexlify() rather than bytes.fromhex() for compatibility with before
# Python 3. However, in Python 3.2 (not 3.3+), unhexlify only accepts a byte
# string.
AKAMAIHD_PV_KEY = unhexlify(
    b"BD938D5EE6D9F42016F9C56577B6FDCF415FE4B184932B785AB32BCADC9BB592")

# Some streams hosted by Akamai seem to require a hdcore parameter
# to function properly.
HDCORE_VERSION = "3.1.0"

# Fragment URL format
FRAGMENT_URL = "{url}{identifier}{quality}Seg{segment}-Frag{fragment}"

Fragment = namedtuple("Fragment", "segment fragment duration url")


class HDSStreamWriter(SegmentedStreamWriter):
    def __init__(self, reader, *args, **kwargs):
        options = reader.stream.session.options
        kwargs["retries"] = options.get("hds-segment-attempts")
        kwargs["threads"] = options.get("hds-segment-threads")
        kwargs["timeout"] = options.get("hds-segment-timeout")
        SegmentedStreamWriter.__init__(self, reader, *args, **kwargs)

        duration, tags = None, []
        if self.stream.metadata:
            duration = self.stream.metadata.value.get("duration")
            tags = [Tag(TAG_TYPE_SCRIPT, timestamp=0,
                        data=self.stream.metadata)]

        self.concater = FLVTagConcat(tags=tags,
                                     duration=duration,
                                     flatten_timestamps=True)

    def fetch(self, fragment, retries=None):
        if self.closed or not retries:
            return

        try:
            return self.session.http.get(fragment.url,
                                         stream=True,
                                         timeout=self.timeout,
                                         exception=StreamError,
                                         **self.stream.request_params)
        except StreamError as err:
            self.logger.error("Failed to open fragment {0}-{1}: {2}",
                              fragment.segment, fragment.fragment, err)
            return self.fetch(fragment, retries - 1)

    def write(self, fragment, res, chunk_size=8192):
        fd = StreamIOIterWrapper(res.iter_content(chunk_size))
        self.convert_fragment(fragment, fd)

    def convert_fragment(self, fragment, fd):
        mdat = None
        try:
            f4v = F4V(fd, raw_payload=True)
            # Fast forward to mdat box
            for box in f4v:
                if box.type == "mdat":
                    mdat = box.payload.data
                    break
        except F4VError as err:
            self.logger.error("Failed to parse fragment {0}-{1}: {2}",
                              fragment.segment, fragment.fragment, err)
            return

        if not mdat:
            self.logger.error("No MDAT box found in fragment {0}-{1}",
                              fragment.segment, fragment.fragment)
            return

        try:
            for chunk in self.concater.iter_chunks(buf=mdat, skip_header=True):
                self.reader.buffer.write(chunk)

                if self.closed:
                    break
            else:
                self.logger.debug("Download of fragment {0}-{1} complete",
                                  fragment.segment, fragment.fragment)
        except IOError as err:
            if "Unknown tag type" in str(err):
                self.logger.error("Unknown tag type found, this stream is "
                                  "probably encrypted")
                self.close()
                return

            self.logger.error("Error reading fragment {0}-{1}: {2}",
                              fragment.segment, fragment.fragment, err)


class HDSStreamWorker(SegmentedStreamWorker):
    def __init__(self, *args, **kwargs):
        SegmentedStreamWorker.__init__(self, *args, **kwargs)

        self.bootstrap = self.stream.bootstrap
        self.current_segment = -1
        self.current_fragment = -1
        self.first_fragment = 1
        self.last_fragment = -1
        self.end_fragment = None

        self.bootstrap_minimal_reload_time = 2.0
        self.bootstrap_reload_time = self.bootstrap_minimal_reload_time
        self.invalid_fragments = set()
        self.live_edge = self.session.options.get("hds-live-edge")

        self.update_bootstrap()

    def update_bootstrap(self):
        self.logger.debug("Updating bootstrap")

        if isinstance(self.bootstrap, Box):
            bootstrap = self.bootstrap
        else:
            bootstrap = self.fetch_bootstrap(self.bootstrap)

        self.live = bootstrap.payload.live
        self.profile = bootstrap.payload.profile
        self.timestamp = bootstrap.payload.current_media_time
        self.identifier = bootstrap.payload.movie_identifier
        self.time_scale = bootstrap.payload.time_scale
        self.segmentruntable = bootstrap.payload.segment_run_table_entries[0]
        self.fragmentruntable = bootstrap.payload.fragment_run_table_entries[0]

        self.first_fragment, last_fragment = self.fragment_count()
        fragment_duration = self.fragment_duration(last_fragment)

        if last_fragment != self.last_fragment:
            bootstrap_changed = True
            self.last_fragment = last_fragment
        else:
            bootstrap_changed = False

        if self.current_fragment < 0:
            if self.live:
                current_fragment = last_fragment

                # Less likely to hit edge if we don't start with last fragment,
                # default buffer is 10 sec.
                fragment_buffer = int(ceil(self.live_edge / fragment_duration))
                current_fragment = max(self.first_fragment,
                                       current_fragment - (fragment_buffer - 1))

                self.logger.debug("Live edge buffer {0} sec is {1} fragments",
                                  self.live_edge, fragment_buffer)

                # Make sure we don't have a duration set when it's a
                # live stream since it will just confuse players anyway.
                self.writer.concater.duration = None
            else:
                current_fragment = self.first_fragment

            self.current_fragment = current_fragment

        self.logger.debug("Current timestamp: {0}", self.timestamp / self.time_scale)
        self.logger.debug("Current segment: {0}", self.current_segment)
        self.logger.debug("Current fragment: {0}", self.current_fragment)
        self.logger.debug("First fragment: {0}", self.first_fragment)
        self.logger.debug("Last fragment: {0}", self.last_fragment)
        self.logger.debug("End fragment: {0}", self.end_fragment)

        self.bootstrap_reload_time = fragment_duration

        if self.live and not bootstrap_changed:
            self.logger.debug("Bootstrap not changed, shortening timer")
            self.bootstrap_reload_time /= 2

        self.bootstrap_reload_time = max(self.bootstrap_reload_time,
                                         self.bootstrap_minimal_reload_time)

    def fetch_bootstrap(self, url):
        res = self.session.http.get(url,
                                    exception=StreamError,
                                    **self.stream.request_params)
        return Box.deserialize(BytesIO(res.content))

    def fragment_url(self, segment, fragment):
        url = absolute_url(self.stream.baseurl, self.stream.url)
        return FRAGMENT_URL.format(url=url,
                                   segment=segment,
                                   fragment=fragment,
                                   identifier="",
                                   quality="")

    def fragment_count(self):
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
            fragment_duration = (fragmentrun.first_fragment_timestamp +
                                 fragmentrun.fragment_duration)

            if self.timestamp > fragment_duration:
                offset = ((self.timestamp - fragment_duration) /
                          fragmentrun.fragment_duration)
                end_fragment += int(offset)

        if first_fragment is None:
            first_fragment = 1

        if end_fragment is None:
            end_fragment = 1

        return first_fragment, end_fragment

    def fragment_duration(self, fragment):
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

    def segment_from_fragment(self, fragment):
        table = self.segmentruntable.payload.segment_run_entry_table

        for segment, start, end in self.iter_segment_table(table):
            if fragment >= (start + 1) and fragment <= (end + 1):
                break
        else:
            segment = 1

        return segment

    def iter_segment_table(self, table):
        # If the first segment in the table starts at the beginning we
        # can go from there, otherwise we start from the end and use the
        # total fragment count to figure out where the last segment ends.
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

    def valid_fragment(self, fragment):
        return fragment not in self.invalid_fragments

    def iter_segments(self):
        while not self.closed:
            fragments = range(self.current_fragment, self.last_fragment + 1)
            fragments = filter(self.valid_fragment, fragments)

            for fragment in fragments:
                self.current_fragment = fragment + 1
                self.current_segment = self.segment_from_fragment(fragment)

                fragment_duration = int(self.fragment_duration(fragment) * 1000)
                fragment_url = self.fragment_url(self.current_segment, fragment)
                fragment = Fragment(self.current_segment, fragment,
                                    fragment_duration, fragment_url)

                self.logger.debug("Adding fragment {0}-{1} to queue",
                                  fragment.segment, fragment.fragment)
                yield fragment

                # End of stream
                stream_end = self.end_fragment and fragment.fragment >= self.end_fragment
                if self.closed or stream_end:
                    return

            if self.wait(self.bootstrap_reload_time):
                try:
                    self.update_bootstrap()
                except StreamError as err:
                    self.logger.warning("Failed to update bootstrap: {0}", err)


class HDSStreamReader(SegmentedStreamReader):
    __worker__ = HDSStreamWorker
    __writer__ = HDSStreamWriter

    def __init__(self, stream, *args, **kwargs):
        SegmentedStreamReader.__init__(self, stream, *args, **kwargs)

        self.logger = stream.session.logger.new_module("stream.hds")


class HDSStream(Stream):
    """
    Implements the Adobe HTTP Dynamic Streaming protocol

    *Attributes:*

    - :attr:`baseurl` Base URL
    - :attr:`url` Base path of the stream, joined with the base URL when
      fetching fragments
    - :attr:`bootstrap` Either a URL pointing to the bootstrap or a
      bootstrap :class:`Box` object used for initial information about
      the stream
    - :attr:`metadata` Either `None` or a :class:`ScriptData` object
      that contains metadata about the stream, such as height, width and
      bitrate
    """

    __shortname__ = "hds"

    def __init__(self, session, baseurl, url, bootstrap, metadata=None,
                 timeout=60, **request_params):
        Stream.__init__(self, session)

        self.baseurl = baseurl
        self.url = url
        self.bootstrap = bootstrap
        self.metadata = metadata
        self.timeout = timeout
        self.request_params = request_params

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
        reader = HDSStreamReader(self)
        reader.open()
        return reader

    @classmethod
    def parse_manifest(cls, session, url, timeout=60, pvswf=None,
                       **request_params):
        """Parses a HDS manifest and returns its substreams.

        :param url: The URL to the manifest.
        :param timeout: How long to wait for data to be returned from
                        from the stream before raising an error.
        :param pvswf: URL of player SWF for Akamai HD player verification.
        """

        if not request_params:
            request_params = {}
            request_params["headers"] = {}
            request_params["params"] = {}

        # These params are reserved for internal use
        request_params.pop("exception", None)
        request_params.pop("stream", None)
        request_params.pop("timeout", None)
        request_params.pop("url", None)

        if "akamaihd" in url:
            request_params["params"]["hdcore"] = HDCORE_VERSION

        res = session.http.get(url, exception=IOError, **request_params)
        manifest = session.http.xml(res, "manifest XML", ignore_ns=True,
                                    exception=IOError)

        parsed = urlparse(url)
        baseurl = manifest.findtext("baseURL")
        baseheight = manifest.findtext("height")
        bootstraps = {}
        streams = {}

        if not baseurl:
            baseurl = urljoin(url, os.path.dirname(parsed.path))

        if not baseurl.endswith("/"):
            baseurl += "/"

        for bootstrap in manifest.findall("bootstrapInfo"):
            name = bootstrap.attrib.get("id") or "_global"
            url = bootstrap.attrib.get("url")

            if url:
                box = absolute_url(baseurl, url)
            else:
                data = base64.b64decode(bytes(bootstrap.text, "utf8"))
                box = Box.deserialize(BytesIO(data))

            bootstraps[name] = box

        pvtoken = manifest.findtext("pv-2.0")
        if pvtoken:
            if not pvswf:
                raise IOError("This manifest requires the 'pvswf' parameter "
                              "to verify the SWF")

            params = cls._pv_params(session, pvswf, pvtoken)
            request_params["params"].update(params)

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
                height = media.attrib.get("height")

                if height:
                    quality = height + "p"
                elif bitrate:
                    quality = bitrate + "k"
                elif streamid:
                    quality = streamid
                elif baseheight:
                    quality = baseheight + "p"
                else:
                    quality = "live"

                metadata = media.findtext("metadata")

                if metadata:
                    metadata = base64.b64decode(bytes(metadata, "utf8"))
                    metadata = ScriptData.deserialize(BytesIO(metadata))
                else:
                    metadata = None

                stream = HDSStream(session, baseurl, url, bootstrap,
                                   metadata=metadata, timeout=timeout,
                                   **request_params)
                streams[quality] = stream

            elif href:
                url = absolute_url(baseurl, href)
                child_streams = cls.parse_manifest(session, url,
                                                   timeout=timeout,
                                                   **request_params)

                for name, stream in child_streams.items():
                    # Override stream name if bitrate is available in parent
                    # manifest but not the child one.
                    bitrate = media.attrib.get("bitrate")

                    if bitrate and not re.match("^(\d+)k$", name):
                        name = bitrate + "k"

                    streams[name] = stream

        return streams

    @classmethod
    def _pv_params(cls, session, pvswf, pv):
        """Returns any parameters needed for Akamai HD player verification.

        Algorithm originally documented by KSV, source:
        http://stream-recorder.com/forum/showpost.php?p=43761&postcount=13
        """

        try:
            data, hdntl = pv.split(";")
        except ValueError:
            data = pv
            hdntl = ""

        cache = Cache(filename="stream.json")
        key = "akamaihd-player:" + pvswf
        cached = cache.get(key)

        headers = dict()
        if cached:
            headers["If-Modified-Since"] = cached["modified"]
        swf = session.http.get(pvswf, headers=headers)

        if cached and swf.status_code == 304:  # Server says not modified
            hash = cached["hash"]
        else:
            # Calculate SHA-256 hash of the uncompressed SWF file, base-64
            # encoded
            hash = sha256()
            hash.update(swfdecompress(swf.content))
            hash = base64.b64encode(hash.digest()).decode("ascii")
            modified = swf.headers.get("Last-Modified", "")

            # Only save in cache if a valid date is given
            if len(modified) < 40:
                cache.set(key, dict(hash=hash, modified=modified))

        msg = "st=0~exp=9999999999~acl=*~data={0}!{1}".format(data, hash)
        auth = hmac.new(AKAMAIHD_PV_KEY, msg.encode("ascii"), sha256)
        pvtoken = "{0}~hmac={1}".format(msg, auth.hexdigest())

        # The "hdntl" parameter can be accepted as a cookie or passed in the
        # query string, but the "pvtoken" parameter can only be in the query
        # string
        params = [("pvtoken", pvtoken)]
        params.extend(parse_qsl(hdntl, keep_blank_values=True))

        return params

