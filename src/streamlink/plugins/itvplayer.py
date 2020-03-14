import json
import logging
import re

from streamlink.compat import urljoin
from streamlink.plugin import Plugin
from streamlink.plugin.api import useragents, validate
from streamlink.plugin.api.utils import itertags
from streamlink.stream import HLSStream, RTMPStream

log = logging.getLogger(__name__)


class ITVPlayer(Plugin):
    _url_re = re.compile(r"https?://(?:www.)?itv.com/hub/(?P<stream>.+)")
    swf_url = "https://mediaplayer.itv.com/2.19.5%2Bbuild.a23aa62b1e/ITVMediaPlayer.swf"
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
        return cls._url_re.match(url) is not None

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
        page = self.session.http.get(self.url)
        for div in itertags(page.text, 'div'):
            if div.attributes.get("id") == "video":
                return div.attributes

    def _get_html5_streams(self, video_info_url):
        video_info = self.video_info()
        res = self.session.http.post(video_info_url,
                                     data=json.dumps(self.device_info),
                                     headers={"hmac": video_info.get("data-video-hmac")})
        data = self.session.http.json(res, schema=self._video_info_schema)

        log.debug("Video ID info response: {0}".format(data))

        stype = data['Playlist']['VideoType']

        for media in data['Playlist']['Video']['MediaFiles']:
            url = urljoin(data['Playlist']['Video']['Base'], media['Href'])
            name_fmt = "{pixels}_{bitrate}" if stype == "CATCHUP" else None
            for s in HLSStream.parse_variant_playlist(self.session, url, name_fmt=name_fmt).items():
                yield s

    def _get_rtmp_streams(self, video_info_url):
        log.debug("XML data path: {0}".format(video_info_url))
        res = self.session.http.get(video_info_url)
        playlist = self.session.http.xml(res, ignore_ns=True)
        mediafiles = playlist.find(".//Playlist/VideoEntries/Video/MediaFiles")
        playpath = mediafiles.find("./MediaFile/URL")
        return {"live": RTMPStream(self.session, {"rtmp": mediafiles.attrib.get("base"),
                                                  "playpath": playpath.text,
                                                  "live": True,
                                                  "swfVfy": self.swf_url
                                                  })}

    def _get_streams(self):
        """
            Find all the streams for the ITV url
            :return: Mapping of quality to stream
        """
        self.session.http.headers.update({"User-Agent": useragents.FIREFOX})
        stream = self._url_re.match(self.url).group("stream")
        video_info = self.video_info()
        video_info_url = video_info.get("data-video-id" if stream.lower() in ("itv", "itv4") else "data-html5-playlist")
        if video_info_url.endswith(".xml"):
            return self._get_rtmp_streams(video_info_url)
        else:
            return self._get_html5_streams(video_info_url)


__plugin__ = ITVPlayer
