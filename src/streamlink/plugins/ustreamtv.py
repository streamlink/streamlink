#!/usr/bin/env python
import json
import logging
import re
from collections import namedtuple
from functools import partial
from operator import itemgetter
from random import randint

from io import BytesIO
from time import sleep

from streamlink import StreamError
from streamlink.compat import urljoin, urlencode
from pymp4.tools.mux import MP4Muxer
from streamlink.plugin import Plugin, PluginOptions
from streamlink.plugin.api import http, validate
from streamlink.stream import HLSStream
from streamlink.stream import HTTPStream
from streamlink.stream import Stream
from streamlink.stream.flvconcat import FLVTagConcat
from streamlink.stream.segmented import SegmentedStreamReader, SegmentedStreamWorker, SegmentedStreamWriter
from websocket import WebSocket

FLVChunk = namedtuple("FLVChunk", "num url offset")
MP4Chunk = namedtuple("MP4Chunk", "num url type is_header")


class UHSDesktopClient(WebSocket):
    WS_URL = "ws://r{0}-1-{1}-{2}-live.ums.ustream.tv:1935/1/ustream"
    APP_ID, APP_VERSION = 3, 1

    def __init__(self, session, media_id, application, **options):
        self.session = session
        self.logger = session.logger.new_module("stream.uhs.flv")
        super(UHSDesktopClient, self).__init__(**options)
        self._callbacks = {}
        self.media_id = media_id
        self.application = application
        self.url = options.pop("url", None)
        self._rsid_a = None
        self._rpin = None
        self._app_id = options.pop("app_id", self.APP_ID)
        self._app_version = options.pop("app_version", self.APP_VERSION)

    def connect(self, **options):
        options.pop("url", None)
        super(UHSDesktopClient, self).connect(self.ws_url, **options)
        self.send_command("connect",
                          {"type": "viewer", "appId": self._app_id, "appVersion": self._app_version, "rsid": self.rsid,
                           "rpin": self.rpin, "referrer": self.url or "unknown", "media": str(self.media_id),
                           "application": self.application}
                          )
        return self

    def __setitem__(self, cmd, f):
        self._callbacks[cmd] = f
        return self

    register = __setitem__

    def recv_command(self):
        data = json.loads(super(UHSDesktopClient, self).recv())
        if data[u"cmd"] in self._callbacks:
            return self._callbacks[data[u"cmd"]](self, **data)
        else:
            self.logger.warning("No handler for command: {}({})", data[u"cmd"], data.get(u"args"))

    @property
    def rsid(self):
        self._rsid_a = self._rsid_a or randint(0, 1e10)
        return "{0:x}:{1:x}".format(self._rsid_a, randint(0, 1e10))

    @property
    def rpin(self):
        self._rpin = self._rpin or randint(0, 1e15)
        return "_rpin.{0:x}".format(self._rpin)

    def send_command(self, command, *args):
        msg = json.dumps({"cmd": command, "args": list(args)}).encode("utf-8")
        self.send(msg)

    @property
    def ws_url(self):
        return self.WS_URL.format(randint(0, 0xffffff), self.media_id, self.application)


class UHSStreamWorker(SegmentedStreamWorker):
    def __init__(self, *args, **kwargs):
        SegmentedStreamWorker.__init__(self, *args, **kwargs)

        self.chunk_id = None
        self.chunk_id_max = None
        self.hashes = {}
        self.providers = []
        self.file_pattern = None
        self.chunk_offsets = {}

        self.stream.client.register("moduleInfo", self.handle_module_info)
        self.stream.client.connect()

    def handle_module_info(self, client, cmd, args):
        raise NotImplementedError

    def drop_old_hashes(self):
        """
        Drop any hashes that are for chunkId ranges that are unused
        """
        chunk_starts = sorted(self.hashes.keys())
        for i, chunk_start in enumerate(chunk_starts[:-1]):
            # if the current chunk id is greater than this chunk start,
            # then it needs to be dropped if the next chunk start is
            # also less than current chunk id
            if self.chunk_id > chunk_start and self.chunk_id > chunk_starts[i + 1]:
                self.hashes.pop(chunk_start)

    def get_chunk_hash(self, chunk_id):
        for chunk_start, chunk_hash in sorted(self.hashes.items(), key=itemgetter(0), reverse=True):
            if chunk_id >= chunk_start:
                return chunk_hash

    def get_chunk_url(self, chunk_id, file_pattern, preferred_provider="uhs_akamai", **params):
        """
        Get the URL for the chunk using the first provider, or prefer a particular provider
        :param file_pattern:
        :param chunk_id:
        :param preferred_provider:
        :return:
        """
        provider_index = 0
        if preferred_provider:
            for i, provider in enumerate(self.providers):
                if provider["name"] == preferred_provider:
                    provider_index = i

        purl = self.providers[provider_index][u"url"]

        return urljoin(purl,
                       file_pattern.replace("%", "%s") % (chunk_id, self.get_chunk_hash(chunk_id))) \
               + "?" + urlencode(params)


class UHSSegmentedFLVStreamWorker(UHSStreamWorker):
    """
    FLV Stream information is formatted differently that MP4 Stream information

    """
    _moduleInfoSchema = [
        {
            validate.optional(u"stream"):
                validate.any(
                    u"offline",
                    {
                        u"hashes": [validate.all({validate.text: validate.text},
                                                 validate.transform(lambda x: dict(map(partial(map, int), x.items())))
                                                 )],
                        u'keyframe': [{u'chunkId': int,
                                       u'offset': int,
                                       u'offsetInMs': int}],
                        u'providers': [{u'name': validate.text,
                                        validate.optional(u'url'): validate.url(),
                                        validate.optional(u'varnishUrl'): validate.url()}],
                        u'streamType': u'flv/segmented',
                        u'streams': [{u'bitrate': int,
                                      u'chunkTime': int,
                                      u'height': int,
                                      u'isTranscoded': bool,
                                      u'streamName': [validate.text],
                                      u'videoCodec': validate.text,
                                      u'width': int}]
                    })
        }
    ]

    def __init__(self, *args, **kwargs):
        super(UHSSegmentedFLVStreamWorker, self).__init__(*args, **kwargs)
        self.chunk_offsets = {}
        self.need_offset = True

    def handle_module_info(self, client, cmd, args):
        data = validate.validate(self._moduleInfoSchema, args)
        if u"stream" in data[0]:
            stream = data[0]["stream"]
            if stream == u"offline":
                return

            # update the hashes for the chunk id
            self.hashes.update(stream.get(u"hashes")[self.stream.stream_index])

            # set the max chunk id to the latest id in the hashes
            self.chunk_id_max = sorted(self.hashes)[-1]
            self.logger.debug("New max chunk_id = {} ".format(self.chunk_id_max))

            # the first chunk is the keyframe chunk, it also has an offset
            self.chunk_id = self.chunk_id or stream[u"keyframe"][self.stream.stream_index][u"chunkId"]
            if self.need_offset:
                self.chunk_offsets[self.chunk_id] = stream[u"keyframe"][self.stream.stream_index][u"offset"]
                self.need_offset = False

            self.providers = stream.get("providers", self.providers)
            self.file_pattern = stream["streams"][self.stream.stream_index]["streamName"][0]

    def iter_segments(self):
        while not self.closed:
            # wait for a command from the web socket server
            self.stream.client.recv_command()
            while self.chunk_id <= self.chunk_id_max - self.reader.live_edge:
                self.logger.debug("Adding chunk {} to queue (offset={})",
                                  self.chunk_id, self.chunk_offsets.get(self.chunk_id, 0))

                yield FLVChunk(self.chunk_id,
                               self.get_chunk_url(self.chunk_id, self.file_pattern),
                               self.chunk_offsets.get(self.chunk_id, 0))
                self.chunk_id += 1


class UHSSegmentedMP4StreamWorker(UHSStreamWorker):
    _moduleInfoSchema = [
        {
            validate.optional(u"stream"): validate.any(
                u"offline",
                {
                    u"chunkId": int,
                    u"hashes": validate.all({validate.text: validate.text},
                                            validate.transform(
                                                lambda x: dict(map(lambda y: (int(y[0]), y[1]), x.items())))),
                    u'providers': [
                        {u'name': validate.text, u'url': validate.url(),
                         validate.optional(u'varnishUrl'): validate.url()}],
                    u'streamType': u'mp4/segmented',
                    u'streams': [validate.any(
                        {u'bitrate': int,
                         u'codec': validate.text,
                         u'contentType': u'video/mp4',
                         u'height': int,
                         u'initUrl': validate.text,
                         u'segmentUrl': validate.text,
                         u'width': int},
                        {u'bitrate': int,
                         u'codec': validate.text,
                         u'contentType': u'audio/mp4',
                         u'initUrl': validate.text,
                         u'segmentUrl': validate.text},
                    )]
                })
        }
    ]

    def __init__(self, *args, **kwargs):
        super(UHSSegmentedMP4StreamWorker, self).__init__(*args, **kwargs)
        self.stream_info = {}

    def handle_module_info(self, client, cmd, args):
        data = validate.validate(self._moduleInfoSchema, args)
        if u"stream" in data[0]:
            stream = data[0]["stream"]
            if stream == u"offline":
                return
            # update the hashes for the chunk id
            self.hashes.update(stream.get(u"hashes"))

            # if the current chunk id is unknown then use the lowest available according to the hashes
            self.chunk_id = self.chunk_id or stream["chunkId"]
            # chunkId is the same for all streams
            self.chunk_id_max = stream["chunkId"]

            self.providers = stream.get("providers", self.providers)
            self.stream_info["audio"] = stream["streams"][self.stream.audio_stream_index]
            self.stream_info["video"] = stream["streams"][self.stream.video_stream_index]

    def iter_segments(self):
        init = True
        while not self.closed:
            # wait for a command from the web socket server
            self.stream.client.recv_command()
            while self.chunk_id <= self.chunk_id_max:
                self.logger.debug("Adding {}chunk {} to queue", "init " if init else "", self.chunk_id)
                url_style = "segmentUrl" if not init else "initUrl"

                yield MP4Chunk(self.chunk_id,
                               self.get_chunk_url(self.chunk_id, self.stream_info["video"][url_style]),
                               "video",
                               init)
                yield MP4Chunk(self.chunk_id,
                               self.get_chunk_url(self.chunk_id, self.stream_info["audio"][url_style]),
                               "audio",
                               init)
                if not init:  # the first video segment has the same chunk id as the first header chunk
                    self.chunk_id += 1
                init = False


class UHSSegmentedFLVStreamWriter(SegmentedStreamWriter):
    def __init__(self, *args, **kwargs):
        SegmentedStreamWriter.__init__(self, *args, **kwargs)

        self.concater = FLVTagConcat(flatten_timestamps=True,
                                     sync_headers=True)

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

    def fetch(self, chunk, retries=0):
        if self.closed:
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
            retries -= 1
            if retries <= 0:
                self.logger.error("Failed to open chunk {0}: {1}", chunk.num, err)
                raise
            sleep(1)
            self.logger.debug("Retrying chunk {0} due to previous error", chunk.num)
            return self.fetch(chunk, retries)


class UHSSegmentedMP4StreamWriter(SegmentedStreamWriter):
    def __init__(self, reader):
        super(UHSSegmentedMP4StreamWriter, self).__init__(reader)
        self.mp4muxer = MP4Muxer(reader.buffer)

        self.done_init = False
        self.chunk_num = 0

    def write(self, chunk, result, chunk_size=8192):
        try:
            stream_id = {"video": 1, "audio": 2}[chunk.type]
            if chunk.is_header:
                self.mp4muxer.add_header(BytesIO(result.content), stream_id)
            else:
                if not self.done_init:
                    self.mp4muxer.finalise_header()
                    self.done_init = True
                elif chunk.num > self.chunk_num:
                    # chunk number has changed, write the new data
                    self.mp4muxer.finalise_content()
                    self.logger.debug("Writing completed chunk to the output buffer: {}".format(self.chunk_num))

                self.mp4muxer.add_content(BytesIO(result.content), stream_id)

            self.chunk_num = chunk.num

            self.logger.debug("Download of {0} for chunk {1} complete", chunk.type, chunk.num)
        except IOError as err:
            self.logger.error("Failed to read {0} chunk {1}: {2}", chunk.type, chunk.num, err)

    def fetch(self, chunk, retries=0):
        if self.closed:
            return

        try:
            # grab all the URLs for the chunk
            return http.get(chunk.url, timeout=self.timeout, exception=StreamError)
        except StreamError as err:
            retries -= 1
            if retries <= 0:
                self.logger.error("Failed to open chunk {0}: {1}", chunk.num, err)
                raise
            sleep(1)  # a short delay between retries
            return self.fetch(chunk, retries)


class UHSSegmentedFLVStreamReader(SegmentedStreamReader):
    __worker__ = UHSSegmentedFLVStreamWorker
    __writer__ = UHSSegmentedFLVStreamWriter

    def __init__(self, stream, live_edge=1, *args, **kwargs):
        self.logger = stream.session.logger.new_module("stream.uhs.flv")
        SegmentedStreamReader.__init__(self, stream, *args, **kwargs)
        self.live_edge = live_edge


class UHSSegmentedMP4StreamReader(SegmentedStreamReader):
    __worker__ = UHSSegmentedMP4StreamWorker
    __writer__ = UHSSegmentedMP4StreamWriter

    def __init__(self, stream, *args, **kwargs):
        self.logger = stream.session.logger.new_module("stream.uhs.mp4")
        SegmentedStreamReader.__init__(self, stream, *args, **kwargs)


class UHSStream(Stream):
    __shortname__ = "uhs"
    __reader__ = None

    def __init__(self, session, url, channel_id, *args, **kwargs):
        Stream.__init__(self, session)
        self.url = url
        self.channel_id = channel_id
        self.client = UHSDesktopClient(session=session, media_id=channel_id, application="channel", url=url)

    def __repr__(self):
        return "<{0}({1!r}, {2!r})>".format(self.__class__.__name__, self.url, self.channel_id)

    def __json__(self):
        jsond = Stream.__json__(self)
        jsond.update({
            "url": self.url,
            "channel_id": self.channel_id
        })
        return jsond

    def open(self):
        if self.__reader__:
            reader = self.__reader__(self)
            reader.open()

            return reader
        else:
            raise NotImplementedError


class UHSSegmentedFLVStream(UHSStream):
    __shortname__ = "uhs.flv/segmented"
    __reader__ = UHSSegmentedFLVStreamReader

    def __init__(self, session, url, channel_id, stream_index, *args, **kwargs):
        super(UHSSegmentedFLVStream, self).__init__(session, url, channel_id)
        self.stream_index = stream_index

    def __json__(self):
        jsond = super(UHSSegmentedFLVStream, self).__json__()
        jsond.update({
            "stream_index": self.stream_index
        })
        return jsond


class UHSSegmentedMP4Stream(UHSStream):
    __shortname__ = "uhs.mp4/segmented"
    __reader__ = UHSSegmentedMP4StreamReader

    def __init__(self, session, url, channel_id, video_stream_index, audio_stream_index, *args, **kwargs):
        super(UHSSegmentedMP4Stream, self).__init__(session, url, channel_id)
        self.video_stream_index = video_stream_index
        self.audio_stream_index = audio_stream_index

    def __json__(self):
        jsond = super(UHSSegmentedMP4Stream, self).__json__()
        jsond.update({
            "video_stream_index": self.video_stream_index,
            "audio_stream_index": self.audio_stream_index,
        })


class UStreamTV(Plugin):
    _url_re = re.compile("""
        http(?:s)?://(?:www\.)?ustream.tv
        (?:
            (?:/embed/|/channel/id/)(?P<channel_id>\d+)
        )?
        (?:
            /recorded/(?P<video_id>\d+)
        )?
    """, re.VERBOSE)

    _channel_id_re = re.compile("\"channelId\":(\d+)")
    _iphone_stream_url = "http://iphone-streaming.ustream.tv/uhls/{channel_id}/streams/live/iphone/playlist.m3u8"

    options = PluginOptions({
        "password": ""
    })

    @classmethod
    def can_handle_url(cls, url):
        return UStreamTV._url_re.match(url)

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
        """
        Get the channel ID, either from the URL in the case of an embedded URL or from the page
        :return:
        """
        channel_id, video_id = UStreamTV._url_re.match(self.url).groups()
        if video_id:
            return None
        elif not channel_id:
            res = http.get(self.url)
            match = UStreamTV._channel_id_re.search(res.text)
            if match:
                return int(match.group(1))
        else:
            return int(channel_id)

    def _get_video_id(self):
        """
        Get the video ID from the URL
        :return: the numeric video_id
        """
        _, video_id = UStreamTV._url_re.match(self.url).groups()
        if video_id:
            return int(video_id)

    def _get_desktop_streams(self, channel_id):
        streams = {}

        def handle_module_info(client, cmd, args):
            if len(args) and u"stream" in args[0]:
                stream_metadata = args[0][u"stream"]
                if stream_metadata == u"offline":
                    self.logger.warning("This stream is currently offline")
                    return
                stream_type = stream_metadata.get("streamType")
                # generate streams for the flv stream type
                if stream_type == "flv/segmented":
                    for stream_index, stream in enumerate(stream_metadata["streams"]):
                        desc = "{0}p".format(stream.get("height"))
                        streams[desc] = UHSSegmentedFLVStream(self.session, client.url, client.media_id,
                                                              stream_index=stream_index)
                elif stream_type == "mp4/segmented":
                    audio_stream_index = None
                    for au_i, audio_stream in enumerate(stream_metadata["streams"]):
                        if (audio_stream[u"contentType"].startswith(u"audio") and
                                (audio_stream_index is None or
                                         audio_stream[u"bitrate"] > stream_metadata["streams"][audio_stream_index][
                                         u"bitrate"])):
                            audio_stream_index = au_i

                    for video_stream_index, video_stream in enumerate(stream_metadata["streams"]):
                        if video_stream[u"contentType"].startswith(u"video"):
                            desc = "{0}p".format(video_stream["height"])
                            streams[desc] = UHSSegmentedMP4Stream(self.session, client.url, client.media_id,
                                                                  video_stream_index, audio_stream_index)
                else:
                    self.logger.warning("Unsupported streamType={0}".format(stream_type))

        ws = UHSDesktopClient(self.session,
                              media_id=channel_id,
                              application="channel",
                              url=self.url).register("moduleInfo", handle_module_info)
        ws.connect().recv_command()
        ws.close()

        return streams

    def _get_mobile_streams(self, channel_id):
        """
        Get the mobile streams
        :param channel_id: the numeric ID of the channel
        :return: a generator of (quality, stream) pairs
        """
        playlist_url = self._iphone_stream_url.format(channel_id=channel_id)
        for name, stream in HLSStream.parse_variant_playlist(self.session, playlist_url).items():
            yield "mobile_{}".format(name), stream

    def _get_recorded_streams(self, video_id):
        streams = {}

        def handle_module_info(client, cmd, args):
            if len(args) and u"stream" in args[0]:
                for stream_metadata in args[0][u"stream"]:
                    for stream in stream_metadata.get(u"streams", []):
                        streams["recorded"] = HTTPStream(self.session, stream[u"streamName"])

        ws = UHSDesktopClient(self.session, app_id=11, app_version=2,
                              media_id=video_id,
                              application="recorded",
                              url=self.url).register("moduleInfo", handle_module_info)
        ws.connect().recv_command()
        ws.close()

        return streams

    def _get_streams(self):
        channel_id = self._get_channel_id()
        streams = {}
        if channel_id:
            self.logger.debug("Getting streams for channel_id: {}".format(channel_id))
            streams.update(self._get_desktop_streams(channel_id))
            streams.update(self._get_mobile_streams(channel_id))
        else:
            video_id = self._get_video_id()
            if video_id:
                self.logger.debug("Getting streams for video_id: {}".format(video_id))
                streams.update(self._get_recorded_streams(video_id))
        return streams


__plugin__ = UStreamTV
