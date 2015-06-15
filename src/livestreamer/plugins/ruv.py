import re

from livestreamer.plugin import Plugin
from livestreamer.stream import RTMPStream

from livestreamer.plugin.api import http

RTMP_LIVE_URL = "rtmp://ruv{0}livefs.fplive.net/ruv{0}live-live/stream{1}"
RTMP_SARPURINN_URL = "rtmp://sipvodfs.fplive.net/sipvod/{0}/{1}{2}.{3}"

_live_url_re = re.compile(r"""^(?:https?://)?(?:www\.)?ruv\.is/
                                (?P<channel_path>
                                    ruv|
                                    ras1|
                                    ras-1|
                                    ras2|
                                    ras-2|
                                    rondo
                                )
                                /?
                                """, re.VERBOSE)

_sarpurinn_url_re = re.compile(r"""^(?:https?://)?(?:www\.)?ruv\.is/sarpurinn/
                                    (?:
                                        ruv|
                                        ruv2|
                                        ruv-2|
                                        ruv-aukaras|
                                        ras1|
                                        ras-1|
                                        ras2|
                                        ras-2
                                    )
                                    /
                                    [a-zA-Z0-9_-]+
                                    /
                                    [0-9]+
                                    /?
                                    """, re.VERBOSE)
_rtmp_url_re = re.compile(r"""rtmp://sipvodfs\.fplive.net/sipvod/
                                (?P<status>
                                    lokad|
                                    opid
                                )
                                /
                                (?P<date>[0-9]+/[0-9][0-9]/[0-9][0-9]/)?
                                (?P<id>[A-Z0-9\$_]+)
                                \.
                                (?P<ext>
                                    mp4|
                                    mp3
                                )""", re.VERBOSE)

_id_map =\
{
    "ruv": "ruv",
    "ras1": "ras1",
    "ras-1": "ras1",
    "ras2": "ras2",
    "ras-2": "ras2",
    "rondo": "ras3"
}


class Ruv(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        if _live_url_re.match(url):
            return _live_url_re.match(url)
        else:
            return _sarpurinn_url_re.match(url)

    def __init__(self, url):
        Plugin.__init__(self, url)
        live_match = _live_url_re.match(url)

        if live_match:
            self.live = True
            self.channel_path = live_match.group("channel_path")
        else:
            self.live = False

    def _get_live_streams(self):
        stream_id = _id_map[self.channel_path]

        streams = {}

        if stream_id == "ruv":
            streams["720p"] = RTMPStream(self.session, {
                "rtmp": RTMP_LIVE_URL.format(stream_id, 1),
                "pageUrl": self.url,
                "live": True
            })
            streams["480p"] = RTMPStream(self.session, {
                "rtmp": RTMP_LIVE_URL.format(stream_id, 2),
                "pageUrl": self.url,
                "live": True
            })
            streams["360p"] = RTMPStream(self.session, {
                "rtmp": RTMP_LIVE_URL.format(stream_id, 3),
                "pageUrl": self.url,
                "live": True
            })
            streams["240p"] = RTMPStream(self.session, {
                "rtmp": RTMP_LIVE_URL.format(stream_id, 4),
                "pageUrl": self.url,
                "live": True
            })
        else:
            streams["audio"] = RTMPStream(self.session, {
                "rtmp": RTMP_LIVE_URL.format(stream_id, 1),
                "pageUrl": self.url,
                "live": True
            })

        return streams

    def _get_sarpurinn_streams(self):
        res = http.get(self.url)
        match = _rtmp_url_re.search(res.text)

        streams = {}
        if not match:
            return streams

        token = match.group("id")
        status = match.group("status")
        extension = match.group("ext")
        date = match.group("date")
        if not date:
            date = ""

        if extension == "mp3":
            key = "audio"
        else:
            key = "576p"

        streams[key] = RTMPStream(self.session, {
            "rtmp": RTMP_SARPURINN_URL.format(status, date, token, extension),
            "pageUrl": self.url,
            "live": True
        })

        return streams

    def _get_streams(self):
        if self.live:
            return self._get_live_streams()
        else:
            return self._get_sarpurinn_streams()


__plugin__ = Ruv
