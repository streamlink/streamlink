import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate, useragents
from streamlink.plugin.api.utils import parse_json
from streamlink.stream import HLSStream, RTMPStream

API_URL = "https://api-dsa.17app.co/api/v1/liveStreams/isUserOnLiveStream"
ROOM_URL = "http://17app.co/share/live/{0}"

_url_re = re.compile(r"http://(17app.co|17.media)/share/(?P<page>[^/]+)/(?P<channel>[^/&?]+)")
_userid_re = re.compile(r'"userID"\s*:\s*"(.+?)"')
_status_re = re.compile(r'"userIsOnLive"\s*:\s*([A-z]+)')
_rtmp_re = re.compile(r'"url"\s*:\s*"(.+?)"')

_user_api_schema = validate.Schema(validate.all(
    {"data": validate.transform(parse_json)},
    validate.get("data"),
    {
        "liveStreamID": int,
        "userIsOnLive": int
    }
))


class App17(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_streams(self):
        match = _url_re.match(self.url)
        page = match.group("page")

        http.headers.update({'User-Agent': useragents.CHROME})

        if page == 'user':
            res = http.get(self.url)
            userid = _userid_re.search(res.text).group(1)
            api = http.post(API_URL, data={"targetUserID": userid})
            data = http.json(api, schema=_user_api_schema)
            rid = data["liveStreamID"]
            if rid == 0:
                self.logger.info("Stream currently unavailable.")
                return

            url = ROOM_URL.format(rid)
            res = http.get(url)
        else:
            res = http.get(self.url)

        status = _status_re.search(res.text)
        if not status:
            return

        if status.group(1) != 'true':
            self.logger.info("Stream currently unavailable.")
            return

        url = _rtmp_re.search(res.text).group(1)
        stream = RTMPStream(self.session, {
                "rtmp": url,
                "live": True
                })
        yield "live", stream

        prefix = url.replace("rtmp:", "http:").replace(".flv", ".m3u8")
        if '.m3u8' not in prefix:
            url = prefix + "/playlist.m3u8"
            for stream in HLSStream.parse_variant_playlist(self.session, url).items():
                yield stream
        else:
            url = prefix
            stream = HLSStream(self.session, url)
            yield "live", stream


__plugin__ = App17
