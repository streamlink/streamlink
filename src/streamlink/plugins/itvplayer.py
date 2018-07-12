import json
import logging
import re

from streamlink.compat import urljoin
from streamlink.plugin import Plugin
from streamlink.plugin.api import http, useragents, validate
from streamlink.plugin.api.utils import itertags
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)


class ITVPlayer(Plugin):
    _url_re = re.compile(r"https?://(?:www.)?itv.com/hub/(?P<stream>.+)")
    _video_info_schema = validate.Schema({
        "StatusCode": 200,
        "AdditionalInfo": {
            "Message": validate.any(None, validate.text)
        },
        "Playlist": {
            "VideoType": validate.text,
            "Video": {
                "Subtitles": validate.any(None, [{
                    "Href": validate.url(),
                }]),
                "Base": validate.url(),
                "MediaFiles": [
                    {"Href": validate.text,
                     "KeyServiceUrl": validate.any(None, validate.url())}
                ]
            }
        }
    })

    @classmethod
    def can_handle_url(cls, url):
        match = cls._url_re.match(url)
        return match is not None

    @property
    def device_info(self):
        return {"user": {},
                "device": {"manufacturer": "Chrome", "model": "66",
                           "os": {"name": "Windows", "version": "10", "type": "desktop"}},
                "client": {"version": "4.1", "id": "browser"},
                "variantAvailability": {"featureset": {"min": ["hls", "aes"],
                                                       "max": ["hls", "aes"]},
                                        "platformTag": "dotcom"}}

    def video_info(self):
        page = http.get(self.url)
        for div in itertags(page.text, 'div'):
            if div.attributes.get("id") == "video":
                return div.attributes

    def _get_streams(self):
        """
            Find all the streams for the ITV url
            :return: Mapping of quality to stream
        """
        http.headers.update({"User-Agent": useragents.FIREFOX})
        video_info = self.video_info()
        video_info_url = video_info.get("data-html5-playlist") or video_info.get("data-video-id")

        res = http.post(video_info_url,
                        data=json.dumps(self.device_info),
                        headers={"hmac": video_info.get("data-video-hmac")})
        data = http.json(res, schema=self._video_info_schema)

        log.debug("Video ID info response: {0}".format(data))

        stype = data['Playlist']['VideoType']

        for media in data['Playlist']['Video']['MediaFiles']:
            url = urljoin(data['Playlist']['Video']['Base'], media['Href'])
            name_fmt = "{pixels}_{bitrate}" if stype == "CATCHUP" else None
            for s in HLSStream.parse_variant_playlist(self.session, url, name_fmt=name_fmt).items():
                yield s



__plugin__ = ITVPlayer
