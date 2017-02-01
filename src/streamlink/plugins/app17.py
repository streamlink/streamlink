import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, useragents
from streamlink.stream import HLSStream, RTMPStream

API_URL = "https://api-dsa.17app.co/api/v1/liveStreams/isUserOnLiveStream"
ROOM_URL = "http://17app.co/share/live/{0}"

_url_re = re.compile(r"http://17app.co/share/(?P<page>[^/]+)/(?P<channel>[^/&?]+)")
_userid_re = re.compile(r'"userID"\s*:\s*"(.+?)"')
_rid_re = re.compile(r'"liveStreamID"\s*:\s*(\d+)')
_status_re = re.compile(r'"userIsOnLive"\s*:\s*([A-z]+)')
_rtmp_re = re.compile(r'"url"\s*:\s*"(.+?)"')


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
            data = {
                "targetUserID": userid
            }
            api = http.post(API_URL, data=data)
            info = re.sub(r'\\', '', api.text)
            rid = _rid_re.search(info).group(1)
            if rid == '0':
                self.logger.info("Stream current unavailable.")
                return

            url = ROOM_URL.format(rid)
            res = http.get(url)
        elif page == 'live':
            res = http.get(self.url)

        if res.status_code != 200:
            self.logger.info("Not a valid room url.")
            return

        status = _status_re.search(res.text).group(1)
        if status != 'true':
            self.logger.info("Stream current unavailable.")
            return

        url = _rtmp_re.search(res.text).group(1)
        stream = RTMPStream(self.session, {
                "rtmp": url,
                "live": True
                })
        yield "live", stream

        prefix = re.sub(r'rtmp:', 'http:', url)
        url = prefix + "/playlist.m3u8"
        for stream in HLSStream.parse_variant_playlist(self.session, url).items():
            yield stream


__plugin__ = App17
