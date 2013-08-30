import re

from collections import defaultdict
from functools import partial
from io import BytesIO, IOBase
from random import randint
from time import sleep
from threading import Thread

from livestreamer.buffers import RingBuffer
from livestreamer.compat import urlparse, urljoin
from livestreamer.exceptions import StreamError, PluginError, NoStreamsError
from livestreamer.plugin import Plugin
from livestreamer.stream import RTMPStream, HLSStream, HTTPStream, Stream
from livestreamer.utils import urlget

from livestreamer.packages.flashmedia import AMFPacket, AMFError
from livestreamer.packages.flashmedia.tag import Header

try:
    import librtmp
    HAS_LIBRTMP = True
except ImportError:
    HAS_LIBRTMP = False


CDN_KEYS = ["cdnStreamUrl", "cdnStreamName"]
PROVIDER_KEYS = ["streams", "name", "url"]

AMF_URL = "http://cgw.ustream.tv/Viewer/getStream/1/{0}.amf"
HLS_PLAYLIST_URL = "http://iphone-streaming.ustream.tv/uhls/{0}/streams/live/iphone/playlist.m3u8"
RECORDED_URL = "http://tcdn.ustream.tv/video/{0}"
RECORDED_URL_PATTERN = r"^(http(s)?://)?(www\.)?ustream.tv/recorded/(?P<video_id>\d+)"
RTMP_URL = "rtmp://channel.live.ums.ustream.tv:80/ustream"
SWF_URL = "http://static-cdn1.ustream.tv/swf/live/viewer.rsl:505.swf"


def valid_cdn(item):
    name, cdn = item
    return all(cdn.get(key) for key in CDN_KEYS)


def valid_provider(info):
    return all(info.get(key) for key in PROVIDER_KEYS)


def validate_module_info(result):
    if (result and isinstance(result, list) and result[0].get("stream")):
        return result[0]


def create_ums_connection(app, media_id, page_url, exception=PluginError):
    params = dict(application=app, media=str(media_id))
    conn = librtmp.RTMP(RTMP_URL, connect_data=params,
                        swfurl=SWF_URL, pageurl=page_url)

    try:
        conn.connect()
    except librtmp.RTMPError:
        raise exception("Failed to connect to RTMP server")

    return conn


class UHSStreamFiller(Thread):
    def __init__(self, stream, conn, provider, stream_index):
        Thread.__init__(self)
        self.daemon = True
        self.running = False

        self.conn = conn
        self.provider = provider
        self.stream_index = stream_index
        self.stream = stream

        self.chunk_ranges = {}
        self.chunk_id = None
        self.chunk_id_max = None

        self.filename_format = ""
        self.header_written = False

    def download_chunk(self, chunk_id):
        self.stream.logger.debug("[{0}] Downloading chunk".format(chunk_id))
        url = self.format_chunk_url(chunk_id)

        attempts = 3
        while attempts and self.running:
            try:
                res = urlget(url, stream=True, exception=IOError, timeout=10)
                break
            except IOError as err:
                self.stream.logger.error("[{0}] Failed to open chunk: {1}".format(
                                         chunk_id, err))
                attempts -= 1
        else:
            return

        while self.running:
            try:
                data = res.raw.read(8192)
            except IOError as err:
                self.stream.logger.error("[{0}] Failed to read chunk {1}".format(
                                         chunk_id, err))
                break

            if not data:
                break

            if not self.header_written:
                flv_header = Header(has_video=True, has_audio=True)
                self.stream.buffer.write(flv_header.serialize())
                self.header_written = True

            self.stream.buffer.write(data)

    def process_module_info(self):
        try:
            result = self.conn.process_packets(invoked_method="moduleInfo",
                                               timeout=30)
        except (IOError, librtmp.RTMPError) as err:
            self.stream.logger.error("Failed to get module info: {0}".format(err))
            return

        result = validate_module_info(result)
        if not result:
            return

        providers = result.get("stream")
        if providers == "offline":
            self.stream.logger.debug("Stream went offline")
            self.stop()
        elif not isinstance(providers, list):
            return

        for provider in providers:
            if provider.get("name") == self.stream.stream.provider:
                break
        else:
            return

        try:
            stream = provider.get("streams")[self.stream_index]
        except IndexError:
            self.stream.logger.debug("Stream index not in result")
            return

        filename_format = stream.get("streamName").replace("%", "%s")
        filename_format = urljoin(provider.get("url"), filename_format)

        self.filename_format = filename_format
        self.update_chunk_info(stream)

    def update_chunk_info(self, result):
        chunk_range = result.get("chunkRange")

        if not chunk_range:
            return

        self.chunk_id_max = int(result.get("chunkId"))
        self.chunk_ranges.update(map(partial(map, int),
                                     chunk_range.items()))

        if self.chunk_id is None:
            self.chunk_id = self.chunk_id_max

    def format_chunk_url(self, chunk_id):
        chunk_hash = ""
        for chunk_start in sorted(self.chunk_ranges):
            if chunk_id >= chunk_start:
                chunk_hash = self.chunk_ranges[chunk_start]

        return self.filename_format % (chunk_id, chunk_hash)

    def run(self):
        self.stream.logger.debug("Starting buffer filler thread")

        while self.running:
            self.check_connection()
            self.process_module_info()

            if self.chunk_id is None:
                continue

            while self.chunk_id <= self.chunk_id_max:
                self.download_chunk(self.chunk_id)
                self.chunk_id += 1

        self.stop()
        self.stream.logger.debug("Buffer filler thread completed")

    def check_connection(self):
        if not self.conn.connected:
            self.stream.logger.error("Disconnected, attempting to reconnect")

            try:
                self.conn = create_ums_connection("channel",
                                                  self.stream.stream.channel_id,
                                                  self.stream.stream.page_url)
            except PluginError as err:
                self.stream.logger.error("Failed to reconnect: {0}", err)
                self.stop()

    def start(self):
        self.running = True

        return Thread.start(self)

    def stop(self):
        self.running = False
        self.conn.close()
        self.stream.buffer.close()


class UHSStreamIO(IOBase):
    def __init__(self, session, stream, timeout=30):
        self.session = session
        self.stream = stream
        self.timeout = timeout

        self.logger = session.logger.new_module("stream.uhs")
        self.buffer = None

    def open(self):
        self.buffer = RingBuffer(self.session.get_option("ringbuffer-size"))

        conn = create_ums_connection("channel",
                                     self.stream.channel_id,
                                     self.stream.page_url,
                                     exception=StreamError)

        self.filler = UHSStreamFiller(self, conn, self.stream.provider,
                                      self.stream.stream_index)
        self.filler.start()

    def read(self, size=-1):
        if not self.buffer:
            return b""

        return self.buffer.read(size, block=self.filler.is_alive(),
                                timeout=self.timeout)

    def close(self):
        self.filler.stop()

        if self.filler.is_alive():
            self.filler.join()


class UHSStream(Stream):
    __shortname__ = "uhs"

    def __init__(self, session, channel_id, page_url, provider,
                 stream_index):
        Stream.__init__(self, session)

        self.channel_id = channel_id
        self.page_url = page_url
        self.provider = provider
        self.stream_index = stream_index

    def __json__(self):
        return dict(channel_id=self.channel_id,
                    page_url=self.page_url,
                    provider=self.provider,
                    stream_index=self.stream_index,
                    **Stream.__json__(self))

    def open(self):
        fd = UHSStreamIO(self.session, self)
        fd.open()

        return fd


class UStreamTV(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return "ustream.tv" in url

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

    def _get_channel_id(self, url):
        match = re.search("ustream.tv/embed/(\d+)", url)
        if match:
            return int(match.group(1))

        match = re.search("\"cid\":(\d+)", urlget(url).text)
        if match:
            return int(match.group(1))

    def _get_hls_streams(self, wait_for_transcode=False):
        # HLS streams are created on demand, so we may have to wait
        # for a transcode to be started.
        attempts = wait_for_transcode and 10 or 1
        playlist_url = HLS_PLAYLIST_URL.format(self.channel_id)
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
        options = dict(rtmp=cdn, app=parsed.path[1:],
                       playpath=stream_name, pageUrl=self.url,
                       swfUrl=SWF_URL, live=True)

        return RTMPStream(self.session, options)

    def _get_module_info(self, app, media_id):
        self.logger.debug("Waiting for moduleInfo invoke")
        conn = create_ums_connection(app, media_id, self.url)

        attempts = 3
        while conn.connected and attempts:
            try:
                result = conn.process_packets(invoked_method="moduleInfo",
                                              timeout=30)
            except (IOError, librtmp.RTMPError) as err:
                raise PluginError("Failed to get stream info: {0}".format(err))

            result = validate_module_info(result)
            if result:
                break
            else:
                attempts -= 1

        conn.close()

        return result

    def _get_streams_from_rtmp(self):
        module_info = self._get_module_info("channel", self.channel_id)
        if not module_info:
            raise NoStreamsError(self.url)

        providers = module_info.get("stream")
        if providers == "offline":
            raise NoStreamsError(self.url)
        elif not isinstance(providers, list):
            raise PluginError("Invalid stream info: {0}".format(providers))

        streams = {}
        for provider in filter(valid_provider, providers):
            provider_url = provider.get("url")
            provider_name = provider.get("name")
            provider_streams = provider.get("streams")

            for stream_index, stream_info in enumerate(provider_streams):
                stream = None
                stream_height = int(stream_info.get("height", 0))
                stream_name = (stream_info.get("description") or
                               (stream_height > 0 and "{0}p".format(stream_height)) or
                               "live")

                if stream_name in streams:
                    provider_name_clean = provider_name.replace("uhs_", "")
                    stream_name += "_alt_{0}".format(provider_name_clean)

                if provider_name.startswith("uhs_"):
                    stream = UHSStream(self.session, self.channel_id,
                                       self.url, provider_name,
                                       stream_index=stream_index)
                elif (provider_url.startswith("rtmp") and
                      RTMPStream.is_usable(self.session)):
                        playpath = stream_info.get("streamName")
                        stream = self._create_rtmp_stream(provider_url,
                                                          playpath)

                if stream:
                    streams[stream_name] = stream

        return streams

    def _get_streams_from_amf(self):
        if not RTMPStream.is_usable(self.session):
            raise NoStreamsError(self.url)

        res = urlget(AMF_URL.format(self.channel_id))

        try:
            packet = AMFPacket.deserialize(BytesIO(res.content))
        except (IOError, AMFError) as err:
            raise PluginError("Failed to parse AMF packet: {0}".format(err))

        for message in packet.messages:
            if message.target_uri == "/1/onResult":
                result = message.value
                break
        else:
            raise PluginError("No result found in AMF packet")

        streams = {}
        stream_name = result.get("streamName")
        if stream_name:
            cdn = result.get("cdnUrl") or result.get("fmsUrl")
            if cdn:
                stream = self._create_rtmp_stream(cdn, stream_name)

                if "videoCodec" in result and result["videoCodec"]["height"] > 0:
                    stream_name = "{0}p".format(int(result["videoCodec"]["height"]))
                else:
                    stream_name = "live"

                streams[stream_name] = stream
            else:
                self.logger.warning("Missing cdnUrl and fmsUrl from result")

        stream_versions = result.get("streamVersions")
        if stream_versions:
            for version, info in stream_versions.items():
                stream_version_cdn = info.get("streamVersionCdn", {})

                for name, cdn in filter(valid_cdn, stream_version_cdn.items()):
                    stream = self._create_rtmp_stream(cdn["cdnStreamUrl"],
                                                      cdn["cdnStreamName"])
                    stream_name = "live_alt_{0}".format(name)
                    streams[stream_name] = stream

        return streams

    def _get_live_streams(self):
        self.channel_id = self._get_channel_id(self.url)

        if not self.channel_id:
            raise NoStreamsError(self.url)

        streams = defaultdict(list)

        if not RTMPStream.is_usable(self.session):
            self.logger.warning("rtmpdump is not usable. "
                                "Not all streams may be available.")

        if HAS_LIBRTMP:
            desktop_streams = self._get_streams_from_rtmp
        else:
            self.logger.warning("python-librtmp is not installed. "
                                "Not all streams may be available.")
            desktop_streams = self._get_streams_from_amf

        try:
            for name, stream in desktop_streams().items():
                streams[name].append(stream)
        except PluginError as err:
            self.logger.error("Unable to fetch desktop streams: {0}", err)
        except NoStreamsError:
            pass

        try:
            mobile_streams = self._get_hls_streams(wait_for_transcode=not streams)
            for name, stream in mobile_streams.items():
                streams[name].append(stream)
        except PluginError as err:
            self.logger.error("Unable to fetch mobile streams: {0}", err)
        except NoStreamsError:
            pass

        return streams

    def _get_recorded_streams(self, video_id):
        streams = {}

        if HAS_LIBRTMP:
            module_info = self._get_module_info("recorded", video_id)
            if not module_info:
                raise NoStreamsError(self.url)

            providers = module_info.get("stream")
            if not isinstance(providers, list):
                raise PluginError("Invalid stream info: {0}".format(providers))

            for provider in providers:
                for stream_info in provider.get("streams"):
                    bitrate = int(stream_info.get("bitrate", 0))
                    stream_name = (bitrate > 0 and "{0}k".format(bitrate) or
                                   "recorded")

                    if stream_name in streams:
                        stream_name += "_alt"

                    stream = HTTPStream(self.session,
                                        stream_info.get("streamName"))
                    streams[stream_name] = stream

        else:
            self.logger.warning("The proper API could not be used without "
                                "python-librtmp installed. Stream URL may be "
                                "incorrect.")

            url = RECORDED_URL.format(video_id)
            random_hash = "{0:02x}{1:02x}".format(randint(0, 255),
                                                  randint(0, 255))
            params = dict(hash=random_hash)
            stream = HTTPStream(self.session, url, params=params)
            streams["recorded"] = stream

        return streams

    def _get_streams(self):
        recorded = re.match(RECORDED_URL_PATTERN, self.url)
        if recorded:
            return self._get_recorded_streams(recorded.group("video_id"))
        else:
            return self._get_live_streams()

__plugin__ = UStreamTV
