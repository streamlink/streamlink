import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import StreamMapper
from streamlink.plugin.api import validate
from streamlink.plugin.api import useragents
from streamlink.stream import HDSStream
from streamlink.stream import HLSStream
from streamlink.stream import HTTPStream
from streamlink.utils import parse_json, parse_xml


class AdultSwim(Plugin):
    API_URL = "http://www.adultswim.com/videos/api/v2/videos/{id}?fields=stream"
    vod_api = " http://www.adultswim.com/videos/api/v0/assets"

    url_re = re.compile(r"""https?://(?:www\.)?adultswim\.com/videos
            (?:/(streams))?
            (?:/([^/]+))?
            (?:/([^/]+))?
            """, re.VERBOSE)
    _stream_data_re = re.compile(r"(?:__)?AS_INITIAL_DATA(?:__)? = (\{.*?});", re.M | re.DOTALL)

    live_schema = validate.Schema({
        u"streams": {
            validate.text: {u"stream": validate.text,
                            validate.optional(u"isLive"): bool,
                            u"archiveEpisodes": [{
                                u"id": validate.text,
                                u"slug": validate.text,
                            }]}}

    })
    vod_id_schema = validate.Schema({u"show": {u"sluggedVideo": {u"id": validate.text}}},
                                    validate.transform(lambda x: x["show"]["sluggedVideo"]["id"]))
    _api_schema = validate.Schema({
        u'status': u'ok',
        u'data': {u'stream': {
            u'assets': [{u'url': validate.url()}]
        }}
    })
    _vod_api_schema = validate.Schema(
        validate.all(
            validate.xml_findall(".//files/file"),
            [validate.xml_element,
             validate.transform(lambda v: {"bitrate": v.attrib.get("bitrate"), "url": v.text})
             ]
        )
    )

    @classmethod
    def can_handle_url(cls, url):
        match = AdultSwim.url_re.match(url)
        return match is not None

    def _make_hls_hds_stream(self, func, stream, *args, **kwargs):
        return func(self.session, stream["url"], *args, **kwargs)

    def _get_show_streams(self, stream_data, show, episode, platform="desktop"):
        video_id = parse_json(stream_data.group(1), schema=self.vod_id_schema)
        res = self.session.http.get(self.vod_api, params={"platform": platform, "id": video_id})

        # create a unique list of the stream manifest URLs
        streams = []
        urldups = []
        for stream in parse_xml(res.text, schema=self._vod_api_schema):
            if stream["url"] not in urldups:
                streams.append(stream)
                urldups.append(stream["url"])

        mapper = StreamMapper(lambda fmt, strm: strm["url"].endswith(fmt))
        mapper.map(".m3u8", self._make_hls_hds_stream, HLSStream.parse_variant_playlist)
        mapper.map(".f4m", self._make_hls_hds_stream, HDSStream.parse_manifest, is_akamai=True)
        mapper.map(".mp4", lambda s: (s["bitrate"] + "k", HTTPStream(self.session, s["url"])))

        for q, s in mapper(streams):
            yield q, s

    def _get_live_stream(self, stream_data, show, episode=None):
        # parse the stream info as json
        stream_info = parse_json(stream_data.group(1), schema=self.live_schema)
        # get the stream ID
        stream_id = None
        show_info = stream_info[u"streams"][show]

        if episode:
            self.logger.debug("Loading replay of episode: {0}/{1}", show, episode)
            for epi in show_info[u"archiveEpisodes"]:
                if epi[u"slug"] == episode:
                    stream_id = epi[u"id"]
        elif show_info.get("isLive") or not len(show_info[u"archiveEpisodes"]):
            self.logger.debug("Loading LIVE streams for: {0}", show)
            stream_id = show_info[u"stream"]
        else:  # off-air
            if len(show_info[u"archiveEpisodes"]):
                epi = show_info[u"archiveEpisodes"][0]
                self.logger.debug("Loading replay of episode: {0}/{1}", show, epi[u"slug"])
                stream_id = epi[u"id"]
            else:
                self.logger.error("This stream is currently offline")
                return

        if stream_id:
            api_url = self.API_URL.format(id=stream_id)

            res = self.session.http.get(api_url, headers={"User-Agent": useragents.SAFARI_8})
            stream_data = self.session.http.json(res, schema=self._api_schema)

            mapper = StreamMapper(lambda fmt, surl: surl.endswith(fmt))
            mapper.map(".m3u8", HLSStream.parse_variant_playlist, self.session)
            mapper.map(".f4m", HDSStream.parse_manifest, self.session)

            stream_urls = [asset[u"url"] for asset in stream_data[u'data'][u'stream'][u'assets']]
            for q, s in mapper(stream_urls):
                yield q, s

        else:
            self.logger.error("Couldn't find the stream ID for this stream: {0}".format(show))

    def _get_streams(self):
        # get the page
        url_match = self.url_re.match(self.url)
        live_stream, show_name, episode_name = url_match.groups()
        if live_stream:
            show_name = show_name or "live-stream"

        res = self.session.http.get(self.url, headers={"User-Agent": useragents.SAFARI_8})
        # find the big blob of stream info in the page
        stream_data = self._stream_data_re.search(res.text)

        if stream_data:
            if live_stream:
                streams = self._get_live_stream(stream_data, show_name, episode_name)
            else:
                self.logger.debug("Loading VOD streams for: {0}/{1}", show_name, episode_name)
                streams = self._get_show_streams(stream_data, show_name, episode_name)

            # De-dup the streams, some of the mobile streams overlap the desktop streams
            dups = set()
            for q, s in streams:
                if hasattr(s, "args") and "url" in s.args:
                    if s.args["url"] not in dups:
                        yield q, s
                        dups.add(s.args["url"])
                else:
                    yield q, s

        else:
            self.logger.error("Couldn't find the stream data for this stream: {0}".format(show_name))


__plugin__ = AdultSwim
