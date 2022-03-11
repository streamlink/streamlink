"""
$description Chinese live streaming platform for live video game broadcasts and live sports game related streams.
$url live.qq.com
$type live
"""

import logging
import re

from streamlink.exceptions import NoStreamsError
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream
from streamlink.utils.parse import parse_json

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(m\.)?live\.qq\.com/(?P<room_id>\d+)"
))
class QQ(Plugin):
    _data_schema = validate.Schema(
        {
            "data": {
                "hls_url": validate.text
            }
        },
        validate.get("data", {}),
        validate.get("hls_url")
    )

    api_url = "http://live.qq.com/api/h5/room?room_id={0}"

    _data_re = re.compile(r"""(?P<data>{.+})""")

    def _get_streams(self):
        room_id = self.match.group("room_id")
        res = self.session.http.get(self.api_url.format(room_id))

        data = self._data_re.search(res.text)
        if not data:
            return

        try:
            hls_url = parse_json(data.group("data"), schema=self._data_schema)
        except Exception:
            raise NoStreamsError(self.url)

        log.debug("URL={0}".format(hls_url))
        return {"live": HLSStream(self.session, hls_url)}


__plugin__ = QQ
