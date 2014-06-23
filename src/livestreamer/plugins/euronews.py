import re

from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http, validate
from livestreamer.stream import HTTPStream, RTMPStream

SWF_URL = "http://euronews.com/media/player_live_1_14.swf"
API_URL_LIVE = "http://euronews.hexaglobe.com/json/"

_url_re = re.compile("http(s)?://(\w+\.)?euronews.com")
_lang_re = re.compile("EN.lang\s+= \"([^\"]+)\";")
_live_check_re = re.compile("swfobject.embedSWF\(\"[^\"]+\", \"streaming-live-player\",")
_video_re = re.compile("{file: \"(?P<url>[^\"]+)\", label: \"(?P<name>[^\"]+)\"}")

_live_schema = validate.Schema({
    validate.any("primary", "secondary"): {
        validate.text: {
            "rtmp_flash": {
                validate.text: {
                    "name": validate.text,
                    "server": validate.url(scheme="rtmp")
                }
            }
        }
    }
})
_schema = validate.Schema(
    validate.union({
        "lang": validate.all(
            validate.transform(_lang_re.search),
            validate.get(1)
        ),
        "live": validate.all(
            validate.transform(_live_check_re.search),
            validate.transform(bool)
        ),
        "videos": validate.all(
            validate.transform(_video_re.findall),
            [(validate.url(scheme="http"), validate.text)]
        )
    })
)


class Euronews(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    def _get_live_streams(self, lang):
        res = http.get(API_URL_LIVE)
        json_res = http.json(res, schema=_live_schema)

        streams = {}
        for site in ("primary", "secondary"):
            for bitrate, stream in json_res[site][lang]["rtmp_flash"].items():
                name = "{0}k".format(bitrate)
                if site == "secondary":
                    name += "_alt"

                stream = RTMPStream(self.session, {
                    "rtmp": stream["server"],
                    "playpath" : stream["name"],
                    "swfUrl": SWF_URL,
                    "live": True
                })
                streams[name] = stream

        return streams

    def _get_video_streams(self, videos):
        streams = {}
        for url, name in videos:
            streams[name] = HTTPStream(self.session, url)

        return streams

    def _get_streams(self):
        res = http.get(self.url, schema=_schema)

        if res["live"]:
            return self._get_live_streams(res["lang"])
        else:
            return self._get_video_streams(res["videso"])


__plugin__ = Euronews
