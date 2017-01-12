#!/usr/bin/env python
import re
from pprint import pprint

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import HDSStream
from streamlink.stream import HLSStream
from streamlink.stream import HTTPStream
from streamlink.utils import parse_json, parse_xml


class AdultSwim(Plugin):
    _user_agent = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_3) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/43.0.2357.65 Safari/537.36")
    API_URL = "http://www.adultswim.com/videos/api/v2/videos/{id}?fields=stream"
    vod_api = " http://www.adultswim.com/videos/api/v0/assets"

    _url_re = re.compile(r"https?://(?:www\.)?adultswim\.com/videos/([^/]*)/?(.*?)/?$")
    _stream_data_re = re.compile(r"(?:__)?AS_INITIAL_DATA(?:__)? = (\{.*?});", re.M | re.DOTALL)

    live_schema = validate.Schema({u"streams": {validate.text: {u"stream": validate.text}}})
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
        match = AdultSwim._url_re.match(url)
        return match is not None

    def _get_vod_streams(self, stream_data, show, episode, platform="desktop"):
        video_id = parse_json(stream_data.group(1), schema=self.vod_id_schema)
        res = http.get(self.vod_api, params={"platform": platform, "id": video_id})
        streams = parse_xml(res.text, schema=self._vod_api_schema)
        urls = set()
        for stream in streams:
            bitrate, url = stream["bitrate"], stream["url"]
            if url not in urls:
                if url.endswith(".mp4"):
                    yield "{0}k".format(bitrate), HTTPStream(self.session, url)
                elif url.endswith(".m3u8"):
                    for s in HLSStream.parse_variant_playlist(self.session, url).items():
                        yield s
                elif url.endswith(".f4m"):
                    for s in HDSStream.parse_manifest(self.session, url, is_akamai=True).items():
                        yield s
                urls.add(stream["url"])

    def _get_live_stream(self, stream_data, stream_name):
            # parse the stream info as json
            stream_info = parse_json(stream_data.group(1), schema=self.live_schema)
            # get the stream ID
            stream_id = stream_info[u"streams"][stream_name][u"stream"]

            if stream_id:
                api_url = self.API_URL.format(id=stream_id)

                res = http.get(api_url, headers={"User-Agent": self._user_agent})
                stream_data = http.json(res, schema=self._api_schema)

                for asset in stream_data[u'data'][u'stream'][u'assets']:
                    for n, s in HLSStream.parse_variant_playlist(self.session, asset[u"url"]).items():
                        yield n, s

            else:
                self.logger.error("Couldn't find the stream ID for this stream: {}".format(stream_name))

    def _get_streams(self):
        # get the page
        url_match = self._url_re.match(self.url)
        show_name = url_match.group(1)
        stream_name = url_match.group(2) or "live-stream"

        res = http.get(self.url, headers={"User-Agent": self._user_agent})
        # find the big blob of stream info in the page
        stream_data = self._stream_data_re.search(res.text)

        if stream_data:
            if show_name == "streams":
                self.logger.debug("Loading LIVE streams for: {0}", stream_name)
                return self._get_live_stream(stream_data, stream_name)
            else:
                self.logger.debug("Loading VOD streams for: {0}/{1}", show_name, stream_name)
                return self._get_vod_streams(stream_data, show_name, stream_name)
        else:
            self.logger.error("Couldn't find the stream data for this stream: {}".format(stream_name))


__plugin__ = AdultSwim
