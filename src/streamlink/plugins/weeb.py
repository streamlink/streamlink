import re

from streamlink.plugin import Plugin, PluginError
from streamlink.plugin.api import http, validate
from streamlink.plugin.api.utils import parse_query
from streamlink.stream import RTMPStream

API_URL = "http://weeb.tv/api/setPlayer"
SWF_URL = "http://static2.weeb.tv/static2/player.swf"
HEADERS = {
    "Referer": SWF_URL
}
PARAMS_KEY_MAP = {
    "0": "status",
    "10": "rtmp",
    "11": "playpath",
    "13": "block_type",
    "14": "block_time",
    "16": "reconnect_time",
    "20": "multibitrate",
    "73": "token"
}
BLOCKED_MSG_FORMAT = (
    "You have crossed the free viewing limit. You have been blocked for "
    "{0} minutes. Try again in {1} minutes"
)
BLOCK_TYPE_VIEWING_LIMIT = 1
BLOCK_TYPE_NO_SLOTS = 11

_url_re = re.compile("http(s)?://(\w+\.)?weeb.tv/(channel|online)/(?P<channel>[^/&?]+)")
_schema = validate.Schema(
    dict,
    validate.map(lambda k, v: (PARAMS_KEY_MAP.get(k, k), v)),
    validate.any(
        {
            "status": validate.transform(int),
            "rtmp": validate.url(scheme="rtmp"),
            "playpath": validate.text,
            "multibitrate": validate.all(
                validate.transform(int),
                validate.transform(bool)
            ),
            "block_type": validate.transform(int),
            validate.optional("token"): validate.text,
            validate.optional("block_time"): validate.text,
            validate.optional("reconnect_time"): validate.text,
        },
        {
            "status": validate.transform(int),
        },
    )
)


class Weeb(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    def _get_streams(self):
        match = _url_re.match(self.url)
        channel_name = match.group("channel")

        form = {
            "cid": channel_name,
            "watchTime": 0,
            "firstConnect": 1,
            "ip": "NaN"
        }
        res = http.post(API_URL, data=form, headers=HEADERS)
        params = parse_query(res.text, schema=_schema)

        if params["status"] <= 0:
            return

        if params["block_type"] != 0:
            if params["block_type"] == BLOCK_TYPE_VIEWING_LIMIT:
                msg = BLOCKED_MSG_FORMAT.format(
                    params.get("block_time", "UNKNOWN"),
                    params.get("reconnect_time", "UNKNOWN")
                )
                raise PluginError(msg)
            elif params["block_type"] == BLOCK_TYPE_NO_SLOTS:
                raise PluginError("No free slots available")
            else:
                raise PluginError("Blocked for unknown reasons")

        if "token" not in params:
            raise PluginError("Server seems busy, retry again later")

        streams = {}
        stream_names = ["sd"]
        if params["multibitrate"]:
            stream_names += ["hd"]

        for stream_name in stream_names:
            playpath = params["playpath"]
            if stream_name == "hd":
                playpath += "HI"

            stream = RTMPStream(self.session, {
                "rtmp": "{0}/{1}".format(params["rtmp"], playpath),
                "pageUrl": self.url,
                "swfVfy": SWF_URL,
                "weeb": params["token"],
                "live": True
            })
            streams[stream_name] = stream

        return streams

__plugin__ = Weeb
