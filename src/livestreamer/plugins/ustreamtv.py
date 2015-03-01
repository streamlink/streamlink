import re

from collections import namedtuple
from functools import partial
from random import randint
from time import sleep

from livestreamer.compat import urlparse, urljoin, range
from livestreamer.exceptions import StreamError, PluginError, NoStreamsError
from livestreamer.plugin import Plugin, PluginOptions
from livestreamer.plugin.api import http, validate
from livestreamer.stream import RTMPStream, HLSStream, HTTPStream, Stream
from livestreamer.stream.flvconcat import FLVTagConcat
from livestreamer.stream.segmented import (
    SegmentedStreamReader, SegmentedStreamWriter, SegmentedStreamWorker
)

try:
    import librtmp
    HAS_LIBRTMP = True
except ImportError:
    HAS_LIBRTMP = False

_url_re = re.compile("""
    http(s)?://(www\.)?ustream.tv
    (?:
        (/embed/|/channel/id/)(?P<channel_id>\d+)
    )?
    (?:
        /recorded/(?P<video_id>\d+)
    )?
""", re.VERBOSE)
_channel_id_re = re.compile("\"cid\":(\d+)")

HLS_PLAYLIST_URL = (
    "http://iphone-streaming.ustream.tv"
    "/uhls/{0}/streams/live/iphone/playlist.m3u8"
)
RECORDED_URL = "http://tcdn.ustream.tv/video/{0}"
RTMP_URL = "rtmp://r{0}-1-{1}-channel-live.ums.ustream.tv:1935/ustream"
SWF_URL = "http://static-cdn1.ustream.tv/swf/live/viewer.rsl:505.swf"

_module_info_schema = validate.Schema(
    list,
    validate.length(1),
    validate.get(0),
    dict
)
_amf3_array = validate.Schema(
    validate.any(
        validate.all(
            {int: object},
            validate.transform(lambda a: list(a.values())),
        ),
        list
    )
)
_recorded_schema = validate.Schema({
    validate.optional("stream"): validate.all(
        _amf3_array,
        [{
            "name": validate.text,
            "streams": validate.all(
                _amf3_array,
                [{
                    "streamName": validate.text,
                    "bitrate": float,
                }],
            ),
            validate.optional("url"): validate.text,
        }]
    )
})
_stream_schema = validate.Schema({
    "name": validate.text,
    "url": validate.text,
    "streams": validate.all(
        _amf3_array,
        [{
            "chunkId": validate.any(int, float),
            "chunkRange": {validate.text: validate.text},
            "chunkTime": validate.any(int, float),
            "offset": validate.any(int, float),
            "offsetInMs": validate.any(int, float),
            "streamName": validate.text,
            validate.optional("bitrate"): validate.any(int, float),
            validate.optional("height"): validate.any(int, float),
            validate.optional("description"): validate.text,
            validate.optional("isTranscoded"): bool
        }],
    )
})
_channel_schema = validate.Schema({
    validate.optional("stream"): validate.any(
        validate.all(
            _amf3_array,
            [_stream_schema],
        ),
        "offline"
    )
})

Chunk = namedtuple("Chunk", "num url offset")


if HAS_LIBRTMP:
    from io import BytesIO
    from time import time

    from librtmp.rtmp import RTMPTimeoutError, PACKET_TYPE_INVOKE
    from livestreamer.packages.flashmedia.types import AMF0Value

    def decode_amf(body):
        def generator():
            fd = BytesIO(body)
            while True:
                try:
                    yield AMF0Value.read(fd)
                except IOError:
                    break

        return list(generator())

    class FlashmediaRTMP(librtmp.RTMP):
        """RTMP connection using python-flashmedia's AMF decoder.

        TODO: Move to python-librtmp instead.
        """

        def process_packets(self, transaction_id=None, invoked_method=None,
                            timeout=None):
            start = time()

            while self.connected and transaction_id not in self._invoke_results:
                if timeout and (time() - start) >= timeout:
                    raise RTMPTimeoutError("Timeout")

                packet = self.read_packet()
                if packet.type == PACKET_TYPE_INVOKE:
                    try:
                        decoded = decode_amf(packet.body)
                    except IOError:
                        continue

                    try:
                        method, transaction_id_, obj = decoded[:3]
                        args = decoded[3:]
                    except ValueError:
                        continue

                    if method == "_result":
                        if len(args) > 0:
                            result = args[0]
                        else:
                            result = None

                        self._invoke_results[transaction_id_] = result
                    else:
                        handler = self._invoke_handlers.get(method)
                        if handler:
                            res = handler(*args)
                            if res is not None:
                                self.call("_result", res,
                                          transaction_id=transaction_id_)

                        if method == invoked_method:
                            self._invoke_args[invoked_method] = args
                            break

                    if transaction_id_ == 1.0:
                        self._connect_result = packet
                    else:
                        self.handle_packet(packet)
                else:
                    self.handle_packet(packet)

            if transaction_id:
                result = self._invoke_results.pop(transaction_id, None)

                return result

            if invoked_method:
                args = self._invoke_args.pop(invoked_method, None)

                return args


def create_ums_connection(app, media_id, page_url, password,
                          exception=PluginError):
    url = RTMP_URL.format(randint(0, 0xffffff), media_id)
    params = {
        "application": app,
        "media": str(media_id),
        "password": password
    }
    conn = FlashmediaRTMP(url,
                          swfurl=SWF_URL,
                          pageurl=page_url,
                          connect_data=params)

    try:
        conn.connect()
    except librtmp.RTMPError:
        raise exception("Failed to connect to RTMP server")

    return conn


class UHSStreamWriter(SegmentedStreamWriter):
    def __init__(self, *args, **kwargs):
        SegmentedStreamWriter.__init__(self, *args, **kwargs)

        self.concater = FLVTagConcat(flatten_timestamps=True,
                                     sync_headers=True)

    def fetch(self, chunk, retries=None):
        if not retries or self.closed:
            return

        try:
            params = {}
            if chunk.offset:
                params["start"] = chunk.offset

            return http.get(chunk.url,
                            timeout=self.timeout,
                            params=params,
                            exception=StreamError)
        except StreamError as err:
            self.logger.error("Failed to open chunk {0}: {1}", chunk.num, err)
            return self.fetch(chunk, retries - 1)

    def write(self, chunk, res, chunk_size=8192):
        try:
            for data in self.concater.iter_chunks(buf=res.content,
                                                  skip_header=not chunk.offset):
                self.reader.buffer.write(data)

                if self.closed:
                    break
            else:
                self.logger.debug("Download of chunk {0} complete", chunk.num)
        except IOError as err:
            self.logger.error("Failed to read chunk {0}: {1}", chunk.num, err)


class UHSStreamWorker(SegmentedStreamWorker):
    def __init__(self, *args, **kwargs):
        SegmentedStreamWorker.__init__(self, *args, **kwargs)

        self.chunk_ranges = {}
        self.chunk_id = None
        self.chunk_id_max = None
        self.chunks = []
        self.filename_format = ""
        self.module_info_reload_time = 2
        self.process_module_info()

    def fetch_module_info(self):
        self.logger.debug("Fetching module info")
        conn = create_ums_connection("channel",
                                     self.stream.channel_id,
                                     self.stream.page_url,
                                     self.stream.password,
                                     exception=StreamError)

        try:
            result = conn.process_packets(invoked_method="moduleInfo",
                                          timeout=10)
        except (IOError, librtmp.RTMPError) as err:
            raise StreamError("Failed to get module info: {0}".format(err))
        finally:
            conn.close()

        result = _module_info_schema.validate(result)
        return _channel_schema.validate(result, "module info")

    def process_module_info(self):
        if self.closed:
            return

        try:
            result = self.fetch_module_info()
        except PluginError as err:
            self.logger.error("{0}", err)
            return

        providers = result.get("stream")
        if not providers or providers == "offline":
            self.logger.debug("Stream went offline")
            self.close()
            return

        for provider in providers:
            if provider.get("name") == self.stream.provider:
                break
        else:
            return

        try:
            stream = provider["streams"][self.stream.stream_index]
        except IndexError:
            self.logger.error("Stream index not in result")
            return

        filename_format = stream["streamName"].replace("%", "%s")
        filename_format = urljoin(provider["url"], filename_format)

        self.filename_format = filename_format
        self.update_chunk_info(stream)

    def update_chunk_info(self, result):
        chunk_range = result["chunkRange"]
        if not chunk_range:
            return

        chunk_id = int(result["chunkId"])
        chunk_offset = int(result["offset"])
        chunk_range = dict(map(partial(map, int), chunk_range.items()))

        self.chunk_ranges.update(chunk_range)
        self.chunk_id_min = sorted(chunk_range)[0]
        self.chunk_id_max = int(result["chunkId"])
        self.chunks = [Chunk(i, self.format_chunk_url(i),
                             not self.chunk_id and i == chunk_id and chunk_offset)
                       for i in range(self.chunk_id_min, self.chunk_id_max + 1)]

        if self.chunk_id is None and self.chunks:
            self.chunk_id = chunk_id

    def format_chunk_url(self, chunk_id):
        chunk_hash = ""
        for chunk_start in sorted(self.chunk_ranges):
            if chunk_id >= chunk_start:
                chunk_hash = self.chunk_ranges[chunk_start]

        return self.filename_format % (chunk_id, chunk_hash)

    def valid_chunk(self, chunk):
        return self.chunk_id and chunk.num >= self.chunk_id

    def iter_segments(self):
        while not self.closed:
            for chunk in filter(self.valid_chunk, self.chunks):
                self.logger.debug("Adding chunk {0} to queue", chunk.num)
                yield chunk

                # End of stream
                if self.closed:
                    return

                self.chunk_id = chunk.num + 1

            if self.wait(self.module_info_reload_time):
                try:
                    self.process_module_info()
                except StreamError as err:
                    self.logger.warning("Failed to process module info: {0}", err)


class UHSStreamReader(SegmentedStreamReader):
    __worker__ = UHSStreamWorker
    __writer__ = UHSStreamWriter

    def __init__(self, stream, *args, **kwargs):
        self.logger = stream.session.logger.new_module("stream.uhs")

        SegmentedStreamReader.__init__(self, stream, *args, **kwargs)


class UHSStream(Stream):
    __shortname__ = "uhs"

    def __init__(self, session, channel_id, page_url, provider,
                 stream_index, password=""):
        Stream.__init__(self, session)

        self.channel_id = channel_id
        self.page_url = page_url
        self.provider = provider
        self.stream_index = stream_index
        self.password = password

    def __repr__(self):
        return "<UHSStream({0!r}, {1!r}, {2!r}, {3!r}, {4!r})>".format(
            self.channel_id, self.page_url, self.provider,
            self.stream_index, self.password
        )

    def __json__(self):
        json = Stream.__json__(self)
        json.update({
            "channel_id": self.channel_id,
            "page_url": self.page_url,
            "provider": self.provider,
            "stream_index": self.stream_index,
            "password": self.password
        })
        return json

    def open(self):
        reader = UHSStreamReader(self)
        reader.open()

        return reader


class UStreamTV(Plugin):
    options = PluginOptions({
        "password": ""
    })

    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    @classmethod
    def stream_weight(cls, stream):
        match = re.match("mobile_(\w+)", stream)
        if match:
            weight, group = Plugin.stream_weight(match.group(1))
            weight -= 1
            group = "mobile_ustream"
        elif stream == "recorded":
            weight, group = 720, "ustream"
        else:
            weight, group = Plugin.stream_weight(stream)

        return weight, group

    def _get_channel_id(self):
        res = http.get(self.url)
        match = _channel_id_re.search(res.text)
        if match:
            return int(match.group(1))

    def _get_hls_streams(self, channel_id, wait_for_transcode=False):
        # HLS streams are created on demand, so we may have to wait
        # for a transcode to be started.
        attempts = wait_for_transcode and 10 or 1
        playlist_url = HLS_PLAYLIST_URL.format(channel_id)
        streams = {}
        while attempts and not streams:
            try:
                streams = HLSStream.parse_variant_playlist(self.session,
                                                           playlist_url,
                                                           nameprefix="mobile_")
            except IOError:
                # Channel is probably offline
                break

            attempts -= 1
            sleep(3)

        return streams

    def _create_rtmp_stream(self, cdn, stream_name):
        parsed = urlparse(cdn)
        params = {
            "rtmp": cdn,
            "app": parsed.path[1:],
            "playpath": stream_name,
            "pageUrl": self.url,
            "swfUrl": SWF_URL,
            "live": True
        }

        return RTMPStream(self.session, params)

    def _get_module_info(self, app, media_id, password="", schema=None):
        self.logger.debug("Waiting for moduleInfo invoke")
        conn = create_ums_connection(app, media_id, self.url, password)

        attempts = 3
        while conn.connected and attempts:
            try:
                result = conn.process_packets(invoked_method="moduleInfo",
                                              timeout=10)
            except (IOError, librtmp.RTMPError) as err:
                raise PluginError("Failed to get stream info: {0}".format(err))

            try:
                result = _module_info_schema.validate(result)
                break
            except PluginError:
                attempts -= 1

        conn.close()

        if schema:
            result = schema.validate(result)

        return result

    def _get_desktop_streams(self, channel_id):
        password = self.options.get("password")
        channel = self._get_module_info("channel", channel_id, password,
                                        schema=_channel_schema)

        if not isinstance(channel.get("stream"), list):
            raise NoStreamsError(self.url)

        streams = {}
        for provider in channel["stream"]:
            provider_url = provider["url"]
            provider_name = provider["name"]
            for stream_index, stream_info in enumerate(provider["streams"]):
                stream = None
                stream_height = int(stream_info.get("height", 0))
                stream_name = stream_info.get("description")
                if not stream_name:
                    if stream_height > 0:
                        if not stream_info.get("isTranscoded"):
                            stream_name = "{0}p+".format(stream_height)
                        else:
                            stream_name = "{0}p".format(stream_height)
                    else:
                        stream_name = "live"

                if stream_name in streams:
                    provider_name_clean = provider_name.replace("uhs_", "")
                    stream_name += "_alt_{0}".format(provider_name_clean)

                if provider_name.startswith("uhs_"):
                    stream = UHSStream(self.session, channel_id,
                                       self.url, provider_name,
                                       stream_index, password)
                elif provider_url.startswith("rtmp"):
                        playpath = stream_info["streamName"]
                        stream = self._create_rtmp_stream(provider_url,
                                                          playpath)

                if stream:
                    streams[stream_name] = stream

        return streams

    def _get_live_streams(self, channel_id):
        has_desktop_streams = False
        if HAS_LIBRTMP:
            try:
                streams = self._get_desktop_streams(channel_id)
                # TODO: Replace with "yield from" when dropping Python 2.
                for stream in streams.items():
                    has_desktop_streams = True
                    yield stream
            except PluginError as err:
                self.logger.error("Unable to fetch desktop streams: {0}", err)
            except NoStreamsError:
                pass
        else:
            self.logger.warning(
                "python-librtmp is not installed, but is needed to access "
                "the desktop streams"
            )

        try:
            streams = self._get_hls_streams(channel_id,
                                            wait_for_transcode=not has_desktop_streams)

            # TODO: Replace with "yield from" when dropping Python 2.
            for stream in streams.items():
                yield stream
        except PluginError as err:
            self.logger.error("Unable to fetch mobile streams: {0}", err)
        except NoStreamsError:
            pass

    def _get_recorded_streams(self, video_id):
        if HAS_LIBRTMP:
            recording = self._get_module_info("recorded", video_id,
                                              schema=_recorded_schema)

            if not isinstance(recording.get("stream"), list):
                return

            for provider in recording["stream"]:
                base_url = provider.get("url")
                for stream_info in provider["streams"]:
                    bitrate = int(stream_info.get("bitrate", 0))
                    stream_name = (bitrate > 0 and "{0}k".format(bitrate) or
                                   "recorded")

                    url = stream_info["streamName"]
                    if base_url:
                        url = base_url + url

                    if url.startswith("http"):
                        yield stream_name, HTTPStream(self.session, url)
                    elif url.startswith("rtmp"):
                        params = dict(rtmp=url, pageUrl=self.url)
                        yield stream_name, RTMPStream(self.session, params)

        else:
            self.logger.warning(
                "The proper API could not be used without python-librtmp "
                "installed. Stream URL is not guaranteed to be valid"
            )

            url = RECORDED_URL.format(video_id)
            random_hash = "{0:02x}{1:02x}".format(randint(0, 255),
                                                  randint(0, 255))
            params = dict(hash=random_hash)
            stream = HTTPStream(self.session, url, params=params)
            yield "recorded", stream

    def _get_streams(self):
        match = _url_re.match(self.url)

        video_id = match.group("video_id")
        if video_id:
            return self._get_recorded_streams(video_id)

        channel_id = match.group("channel_id") or self._get_channel_id()
        if channel_id:
            return self._get_live_streams(channel_id)

__plugin__ = UStreamTV
