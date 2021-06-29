import logging
import random
import re
from urllib.parse import parse_qsl, urlparse

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream, HTTPStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(www\.)?liveme\.com/live\.html\?videoid=(\d+)"
))
class LiveMe(Plugin):
    api_url = "https://live.ksmobile.net/live/queryinfo"
    api_schema = validate.Schema(validate.all({
        "status": "200",
        "data": {
            "video_info": {
                "videosource": validate.any('', validate.url()),
                "hlsvideosource": validate.any('', validate.url()),
            }
        }
    }, validate.get("data")))

    def _random_t(self, t):
        return "".join(random.choice("ABCDEFGHJKMNPQRSTWXYZabcdefhijkmnprstwxyz2345678") for _ in range(t))

    def _make_stream(self, url):
        if url and url.endswith("flv"):
            return HTTPStream(self.session, url)
        elif url and url.endswith("m3u8"):
            return HLSStream(self.session, url)

    def _get_streams(self):
        url_params = dict(parse_qsl(urlparse(self.url).query))
        video_id = url_params.get("videoid")

        if video_id:
            vali = '{0}l{1}m{2}'.format(self._random_t(4), self._random_t(4), self._random_t(5))
            data = {
                'userid': 1,
                'videoid': video_id,
                'area': '',
                'h5': 1,
                'vali': vali
            }
            log.debug("Found Video ID: {0}".format(video_id))
            res = self.session.http.post(self.api_url, data=data)
            data = self.session.http.json(res, schema=self.api_schema)
            hls = self._make_stream(data["video_info"]["hlsvideosource"])
            video = self._make_stream(data["video_info"]["videosource"])
            if hls:
                yield "live", hls
            if video:
                yield "live", video


__plugin__ = LiveMe
