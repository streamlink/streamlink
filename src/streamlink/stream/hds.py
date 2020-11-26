import base64
import hmac
import logging
import os.path
import random
import re
import string
from binascii import unhexlify
from collections import namedtuple
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
from math import ceil
from urllib.parse import parse_qsl, urljoin, urlparse, urlunparse

from streamlink.cache import Cache
from streamlink.exceptions import PluginError, StreamError
from streamlink.packages.flashmedia import F4V, F4VError
from streamlink.packages.flashmedia.box import Box
from streamlink.packages.flashmedia.tag import ScriptData, TAG_TYPE_SCRIPT, Tag
from streamlink.stream.flvconcat import FLVTagConcat
from streamlink.stream.segmented import (SegmentedStreamReader, SegmentedStreamWorker, SegmentedStreamWriter)
from streamlink.stream.stream import Stream
from streamlink.stream.wrappers import StreamIOIterWrapper
from streamlink.utils import absolute_url, swfdecompress

log = logging.getLogger(__name__)
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
            request_params = self.stream.request_params.copy()
            params = request_params.pop("params", {})
            params.pop("g", None)
            return self.session.http.get(fragment.url,
                                         stream=True,
                                         timeout=self.timeout,
                                         exception=StreamError,
                                         params=params,
                                         **request_params)
        except StreamError as err:
            log.error(f"Failed to open fragment {fragment.segment}-{fragment.fragment}: {err}")
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
            log.error(f"Failed to parse fragment {fragment.segment}-{fragment.fragment}: {err}")
            return

        if not mdat:
            log.error(f"No MDAT box found in fragment {fragment.segment}-{fragment.fragment}")
            return

        try:
            for chunk in self.concater.iter_chunks(buf=mdat, skip_header=True):
                self.reader.buffer.write(chunk)

                if self.closed:
                    break
            else:
                log.debug(f"Download of fragment {fragment.segment}-{fragment.fragment} complete")
        except OSError as err:
            if "Unknown tag type" in str(err):
                log.error("Unknown tag type found, this stream is probably encrypted")
                self.close()
                return

            log.error(f"Error reading fragment {fragment.segment}-{fragment.fragment}: {err}")


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
        log.debug("Updating bootstrap")

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

                log.debug(f"Live edge buffer {self.live_edge} sec is {fragment_buffer} fragments")

                # Make sure we don't have a duration set when it's a
                # live stream since it will just confuse players anyway.
                self.writer.concater.duration = None
            else:
                current_fragment = self.first_fragment

            self.current_fragment = current_fragment

        log.debug(f"Current timestamp: {self.timestamp / self.time_scale}")
        log.debug(f"Current segment: {self.current_segment}")
        log.debug(f"Current fragment: {self.current_fragment}")
        log.debug(f"First fragment: {self.first_fragment}")
        log.debug(f"Last fragment: {self.last_fragment}")
        log.debug(f"End fragment: {self.end_fragment}")

        self.bootstrap_reload_time = fragment_duration

        if self.live and not bootstrap_changed:
            log.debug("Bootstrap not changed, shortening timer")
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
            fragment_duration = fragmentrun.first_fragment_timestamp + fragmentrun.fragment_duration

            if self.timestamp > fragment_duration:
                offset = (self.timestamp - fragment_duration) / fragmentrun.fragment_duration
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
                        prev = table[i - 1]
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
            if start - 1 <= fragment <= end:
                return segment
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

                log.debug(f"Adding fragment {fragment.segment}-{fragment.fragment} to queue")
                yield fragment

                # End of stream
                stream_end = self.end_fragment and fragment.fragment >= self.end_fragment
                if self.closed or stream_end:
                    return

            if self.wait(self.bootstrap_reload_time):
                try:
                    self.update_bootstrap()
                except StreamError as err:
                    log.warning(f"Failed to update bootstrap: {err}")


class HDSStreamReader(SegmentedStreamReader):
    __worker__ = HDSStreamWorker
    __writer__ = HDSStreamWriter

    def __init__(self, stream, *args, **kwargs):
        SegmentedStreamReader.__init__(self, stream, *args, **kwargs)


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

        # Deep copy request params to make it mutable
        self.request_params = deepcopy(request_params)

        parsed = urlparse(self.url)
        if parsed.query:
            params = parse_qsl(parsed.query)
            if params:
                if not self.request_params.get("params"):
                    self.request_params["params"] = {}

                self.request_params["params"].update(params)

        self.url = urlunparse(
            (parsed.scheme, parsed.netloc, parsed.path, None, None, None)
        )

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
                    url=self.url, bootstrap=bootstrap, metadata=metadata,
                    params=self.request_params.get("params", {}),
                    headers=self.request_params.get("headers", {}))

    def open(self):
        reader = HDSStreamReader(self)
        reader.open()
        return reader

    @classmethod
    def parse_manifest(cls, session, url, timeout=60, pvswf=None, is_akamai=False,
                       **request_params):
        """Parses a HDS manifest and returns its substreams.

        :param url: The URL to the manifest.
        :param timeout: How long to wait for data to be returned from
                        from the stream before raising an error.
        :param is_akamai: force adding of the akamai parameters
        :param pvswf: URL of player SWF for Akamai HD player verification.
        """
        # private argument, should only be used in recursive calls
        raise_for_drm = request_params.pop("raise_for_drm", False)

        if not request_params:
            request_params = {}

        request_params["headers"] = request_params.get("headers", {})
        request_params["params"] = request_params.get("params", {})

        # These params are reserved for internal use
        request_params.pop("exception", None)
        request_params.pop("stream", None)
        request_params.pop("timeout", None)
        request_params.pop("url", None)

        if "akamaihd" in url or is_akamai:
            request_params["params"]["hdcore"] = HDCORE_VERSION
            request_params["params"]["g"] = cls.cache_buster_string(12)

        res = session.http.get(url, exception=IOError, **request_params)
        manifest = session.http.xml(res, "manifest XML", ignore_ns=True,
                                    exception=IOError)

        if manifest.findtext("drmAdditionalHeader"):
            log.debug(f"Omitting HDS stream protected by DRM: {url}")
            if raise_for_drm:
                raise PluginError("{} is protected by DRM".format(url))
            log.warning("Some or all streams are unavailable as they are protected by DRM")
            return {}

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
                raise OSError("This manifest requires the 'pvswf' parameter "
                              "to verify the SWF")

            params = cls._pv_params(session, pvswf, pvtoken, **request_params)
            request_params["params"].update(params)

        child_drm = False

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
                try:
                    child_streams = cls.parse_manifest(session, url,
                                                       timeout=timeout,
                                                       is_akamai=is_akamai,
                                                       raise_for_drm=True,
                                                       **request_params)
                except PluginError:
                    child_drm = True
                    child_streams = {}

                for name, stream in child_streams.items():
                    # Override stream name if bitrate is available in parent
                    # manifest but not the child one.
                    bitrate = media.attrib.get("bitrate")

                    if bitrate and not re.match(r"^(\d+)k$", name):
                        name = bitrate + "k"

                    streams[name] = stream
        if child_drm:
            log.warning("Some or all streams are unavailable as they are protected by DRM")

        return streams

    @classmethod
    def _pv_params(cls, session, pvswf, pv, **request_params):
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

        request_params = deepcopy(request_params)
        headers = request_params.pop("headers", {})
        if cached:
            headers["If-Modified-Since"] = cached["modified"]
        swf = session.http.get(pvswf, headers=headers, **request_params)

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

    @staticmethod
    def cache_buster_string(length):
        return "".join([random.choice(string.ascii_uppercase) for i in range(length)])
