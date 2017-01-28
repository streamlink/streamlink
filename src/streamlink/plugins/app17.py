import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate, useragents
from streamlink.stream import HLSStream, RTMPStream

API_URL = "https://api-dsa.17app.co/api/v1/liveStreams/isUserOnLiveStream"
ROOM_URL = "http://17app.co/share/live/{0}"

_url_re = re.compile(r"http://17app.co/share/user/(?P<channel>[^/&?]+)")
_userid_re = re.compile(r'"userID"\s*:\s*"(.+?)"')
_rid_re = re.compile(r'"liveStreamID"\s*:\s*(\d+)')
_status_re = re.compile(r'"userIsOnLive"\s*:\s*(\d+)')
_rtmp_re = re.compile(r'"url"\s*:\s*"(.+?)"')


class App17(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_streams(self):
        match = _url_re.match(self.url)
        channel = match.group("channel")

        http.headers.update({'User-Agent': useragents.CHROME})

        res = http.get(self.url)
        userid = _userid_re.search(res.text).group(1)
        data = {
            "targetUserID": userid
        }
        api = http.post(API_URL, data=data)
        info = re.sub(r'\\', '', api.text)

        status = _status_re.search(info).group(1)
        if status != '1':
            self.logger.info("Channel offline now!")
            return

        rid = _rid_re.search(info).group(1)
        url = ROOM_URL.format(rid)
        res = http.get(url)
        url = _rtmp_re.search(res.text).group(1)
        stream = RTMPStream(self.session, {
                "rtmp": url,
                "live": True
                })
        yield "live", stream

        prefix = re.sub(r'rtmp:', 'http:', url)
        url = prefix + "/playlist.m3u8"
        stream = HLSStream(self.session, url)
        yield "hls", stream


__plugin__ = App17
