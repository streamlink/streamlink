import re

from streamlink.compat import urlparse
from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import RTMPStream

LIVE_STREAM_URL = "rtmp://stream1.cybergame.tv:2936/live/"
PLAYLIST_URL = "http://api.cybergame.tv/p/playlist.smil"

_url_re = re.compile(r"""
    http(s)?://(\w+\.)?cybergame.tv
    (?:
        /videos/(?P<video_id>\d+)
    )?
    (?:
        /(?P<channel>[^/&?]+)
    )?
""", re.VERBOSE)

_playlist_schema = validate.Schema(
    validate.union({
        "base": validate.all(
            validate.xml_find("./head/meta"),
            validate.get("base"),
            validate.url(scheme="rtmp")
        ),
        "videos": validate.all(
            validate.xml_findall(".//video"),
            [
                validate.union({
                    "src": validate.all(
                        validate.get("src"),
                        validate.text
                    ),
                    "height": validate.all(
                        validate.get("height"),
                        validate.text,
                        validate.transform(int)
                    )
                })
            ]
        )
    })
)


class Cybergame(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_playlist(self, **params):
        res = self.session.http.get(PLAYLIST_URL, params=params)
        playlist = self.session.http.xml(res, schema=_playlist_schema)
        streams = {}
        for video in playlist["videos"]:
            name = "{0}p".format(video["height"])
            stream = RTMPStream(self.session, {
                "rtmp": "{0}/{1}".format(playlist["base"], video["src"]),
                "app": urlparse(playlist["base"]).path[1:],
                "pageUrl": self.url,
                "rtmp": playlist["base"],
                "playpath": video["src"],
                "live": True
            })
            streams[name] = stream

        return streams

    def _get_streams(self):
        match = _url_re.match(self.url)
        video_id = match.group("video_id")
        channel = match.group("channel")

        if video_id:
            return self._get_playlist(vod=video_id)
        elif channel:
            return {'live': RTMPStream(
                self.session,
                dict(rtmp=LIVE_STREAM_URL, app="live", pageUrl=self.url, playpath=channel, live=True)
            )}


__plugin__ = Cybergame
