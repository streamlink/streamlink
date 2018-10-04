import logging
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HTTPStream
from streamlink.utils import parse_json

log = logging.getLogger(__name__)


class Egame(Plugin):

    STREAM_WEIGHTS = {
        "source": 65535,
        # "sd6m": 6000,
        # "sd4m": 4000,
        # "sd": 3000,
        # "hd": 1500,
        # "medium": 1024,
        # "low": 900,
    }

    _url_re = re.compile(r"https://egame\.qq\.com/(?P<channel>\d+)")
    _room_json_re = re.compile(r"window\._playerInfo\s*=\s*({.*});")

    data_schema = validate.Schema({
        "vid": validate.text,
        "urlArray": [{"playUrl": validate.text}],
    })

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url)

    @classmethod
    def stream_weight(cls, stream):
        if stream in cls.STREAM_WEIGHTS:
            return cls.STREAM_WEIGHTS[stream], "egame"
        return Plugin.stream_weight(stream)

    def _get_streams(self):
        res = self.session.http.get(self.url)
        m = self._room_json_re.search(res.text)
        if not m:
            log.info("Stream currently unavailable.")
            return

        data = parse_json(m.group(1), schema=self.data_schema)
        # 1. some stream url has bitrate ending with t like _1500t.flv
        # 2. data["vid"] is required because some stream IDs are to short and
        #    it could result in a wrong bitrate for source.
        bitrate_re = re.compile(r"%s_(\d{3,4})\w?\.flv" % data["vid"])
        for d in data["urlArray"]:
            url = d["playUrl"]
            match = bitrate_re.search(url)
            if match:
                stream_name = "{0}k".format(int(match.group(1)))
            else:
                stream_name = "source"
            yield stream_name, HTTPStream(self.session, url)


__plugin__ = Egame
