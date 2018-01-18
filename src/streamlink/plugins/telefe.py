import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, useragents, validate
from streamlink.stream import HLSStream, HTTPStream
from streamlink.utils import parse_json


class Telefe(Plugin):
    _url_re = re.compile(r'https?://telefe.com/.+')

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url)

    def _get_streams(self):
        res = http.get(self.url, headers={'User-Agent': useragents.CHROME})
        video_search = res.text
        video_search = video_search[video_search.index('{"top":{"view":"PlayerContainer","model":{'):]
        video_search = video_search[: video_search.index('}]}}') + 4] + "}"

        video_url_found_hls = ""
        video_url_found_http = ""

        json_video_search = parse_json(video_search)
        json_video_search_sources = json_video_search["top"]["model"]["videos"][0]["sources"]
        self.logger.debug('Video ID found: {0}', json_video_search["top"]["model"]["id"])
        for current_video_source in json_video_search_sources:
            if "HLS" in current_video_source["type"]:
                video_url_found_hls = "http://telefe.com" + current_video_source["url"]
                self.logger.debug("HLS content available")
            if "HTTP" in current_video_source["type"]:
                video_url_found_http = "http://telefe.com" + current_video_source["url"]
                self.logger.debug("HTTP content available")

        http.headers = {'Referer': self.url,
                        'User-Agent': useragents.CHROME,
                        'X-Requested-With': 'ShockwaveFlash/25.0.0.148'}

        if video_url_found_hls:
            hls_streams = HLSStream.parse_variant_playlist(self.session, video_url_found_hls)
            for s in hls_streams.items():
                yield s

        if video_url_found_http:
            yield "http", HTTPStream(self.session, video_url_found_http)


__plugin__ = Telefe
