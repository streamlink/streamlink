"""
$description Chinese live-streaming platform for live video game broadcasts and live sports game related streams.
$url live.qq.com
$type live
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream
from streamlink.utils.url import update_scheme


log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(m\.)?live\.qq\.com/(?P<room_id>\d+)?"
))
class QQ(Plugin):
    _URL_API = "https://live.qq.com/api/h5/room"

    def _get_streams(self):
        room_id = self.match.group("room_id")

        if not room_id:
            room_id = self.session.http.get(self.url, schema=validate.Schema(
                validate.parse_html(),
                validate.xml_xpath_string(".//*[@data-rid][1]/@data-rid"),
            ))
        if not room_id:
            return

        error, data = self.session.http.get(
            self._URL_API,
            params={"room_id": room_id},
            schema=validate.Schema(
                validate.parse_json(),
                validate.any(
                    validate.all(
                        {
                            "error": 0,
                            "data": {
                                "nickname": str,
                                "game_name": str,
                                "room_name": str,
                                "hls_url": validate.url(path=validate.endswith(".m3u8")),
                            }
                        },
                    ),
                    validate.all(
                        {
                            "error": int,
                            "data": str,
                        },
                    ),
                ),
                validate.union_get("error", "data"),
            ),
        )
        if error != 0:
            log.error(data)
            return

        self.id = room_id
        self.author = data["nickname"]
        self.category = data["game_name"]
        self.title = data["room_name"]

        hls_url = update_scheme("https://", data["hls_url"], force=True)

        return {"live": HLSStream(self.session, hls_url)}


__plugin__ = QQ
