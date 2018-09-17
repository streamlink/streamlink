import re
import json
from streamlink.plugin import Plugin
from streamlink.stream import HTTPStream

_url_re = re.compile(r"https://egame\.qq\.com/(?P<channel>[^/&?]+)")
_room_json = re.compile(r'EgamePlayer\.Player\(({.*})\);')
#some stream url has bitrate ending with t like _1500t.flv
_stream_bitrate = re.compile(r'_(\d{3,4})\w?\.flv')

STREAM_WEIGHTS = {
        "source": 65535,
        "sd6m": 6000,
        "sd4m": 4000,
        "sd": 3000,
        "hd": 1500,
        "medium": 1024,
        "low": 900
}


class Egame(Plugin):

        @classmethod
        def can_handle_url(cls, url):
                return _url_re.match(url)

        @classmethod
        def stream_weight(cls, stream):
                if stream in STREAM_WEIGHTS:
                        return STREAM_WEIGHTS[stream], "egame"
                return Plugin.stream_weight(stream)

        def _get_streams(self):
                res = self.session.http.get(self.url)
                try:
                        roominfo_text = _room_json.search(res.text).group(1)
                except:
                        self.logger.info("Stream not available.")
                        return

                roominfo_json = json.loads(roominfo_text)

                num_streams = len(roominfo_json['urlArray'])
                for i in range(num_streams):
                        match = _stream_bitrate.search(roominfo_json['urlArray'][i]['playUrl'])
                        stream_name = None
                        if not match:
                                stream_name = "source"
                        else:
                                bitrate = int(match.group(1))
                                for _name, val in STREAM_WEIGHTS.items():
                                        if bitrate == val:
                                                stream_name = _name
                        yield stream_name, HTTPStream(self.session, roominfo_json['urlArray'][i]['playUrl'])
                return

__plugin__ = Egame

