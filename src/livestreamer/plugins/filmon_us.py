import re

from livestreamer.compat import urlparse
from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http, validate
from livestreamer.plugin.api.utils import parse_json, parse_query
from livestreamer.stream import RTMPStream, HTTPStream

SWF_LIVE_URL = "https://www.filmon.com/tv/modules/FilmOnTV/files/flashapp/filmon/FilmonPlayer.swf"
SWF_VIDEO_URL = "http://www.filmon.us/application/themes/base/flash/MediaPlayer.swf"

_url_re = re.compile("http(s)?://(\w+\.)?filmon.us")
_live_export_re = re.compile(
    "<iframe src=\"(https://www.filmon.com/channel/export[^\"]+)\""
)
_live_json_re = re.compile("var startupChannel = (.+);")
_replay_json_re = re.compile("var standByVideo = encodeURIComponent\('(.+)'\);")
_history_re = re.compile(
    "helpers.common.flash.flashplayerinstall\({url:'([^']+)',"
)
_video_flashvars_re = re.compile(
    "<embed width=\"486\" height=\"326\" flashvars=\"([^\"]+)\""
)

_live_schema = validate.Schema({
    "streams": [{
        "name": validate.text,
        "quality": validate.text,
        "url": validate.url(scheme="rtmp")
    }]
})
_schema = validate.Schema(
    validate.union({
        "export_url": validate.all(
            validate.transform(_live_export_re.search),
            validate.any(
                None,
                validate.get(1),
            )
        ),
        "video_flashvars": validate.all(
            validate.transform(_video_flashvars_re.search),
            validate.any(
                None,
                validate.all(
                    validate.get(1),
                    validate.transform(parse_query),
                    {
                        "_111pix_serverURL": validate.url(scheme="rtmp"),
                        "en_flash_providerName": validate.text
                    }
                )
            )
        ),
        "history_video": validate.all(
            validate.transform(_history_re.search),
            validate.any(
                None,
                validate.all(
                    validate.get(1),
                    validate.url(scheme="http")
                )
            )
        ),
        "standby_video": validate.all(
            validate.transform(_replay_json_re.search),
            validate.any(
                None,
                validate.all(
                    validate.get(1),
                    validate.transform(parse_json),
                    [{
                        "streamName": validate.url(scheme="http")
                    }]
                )
            )
        )
    })
)

class Filmon_us(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    def _get_live_stream(self, export_url):
        res = http.get(export_url)
        match = _live_json_re.search(res.text)
        if not match:
            return

        json = parse_json(match.group(1), schema=_live_schema)
        streams = {}
        for stream in json["streams"]:
            stream_name = stream["quality"]
            parsed = urlparse(stream["url"])

            stream = RTMPStream(self.session, {
                "rtmp": stream["url"],
                "app": "{0}?{1}".format(parsed.path[1:], parsed.query),
                "playpath": stream["name"],
                "swfVfy": SWF_LIVE_URL,
                "pageUrl": self.url,
                "live": True
            })
            streams[stream_name] = stream

        return streams

    def _get_streams(self):
        res = http.get(self.url, schema=_schema)

        if res["export_url"]:
            return self._get_live_stream(res["export_url"])
        elif res["video_flashvars"]:
            stream = RTMPStream(self.session, {
                "rtmp": res["video_flashvars"]["_111pix_serverURL"],
                "playpath": res["video_flashvars"]["en_flash_providerName"],
                "swfVfy": SWF_VIDEO_URL,
                "pageUrl": self.url
            })
            return dict(video=stream)
        elif res["standby_video"]:
            for stream in res["standby_video"]:
                stream = HTTPStream(self.session, stream["streamName"])
                return dict(replay=stream)
        elif res["history_video"]:
            stream = HTTPStream(self.session, res["history_video"])
            return dict(history=stream)

        return

__plugin__ = Filmon_us
