# -*- coding: utf-8 -*-
import re

from streamlink.exceptions import NoStreamsError
from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.plugin.api import validate
from streamlink.plugin.api.utils import parse_json
from streamlink.stream import HLSStream


class QQ(Plugin):
    """Streamlink Plugin for live.qq.com"""

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
    _url_re = re.compile(r"""https?://(m\.)?live\.qq\.com/(?P<room_id>\d+)""")

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url)

    def _get_streams(self):
        match = self._url_re.match(self.url)
        if not match:
            return

        room_id = match.group("room_id")
        res = http.get(self.api_url.format(room_id))

        data = self._data_re.search(res.text)
        if not data:
            return

        try:
            hls_url = parse_json(data.group("data"), schema=self._data_schema)
        except Exception as e:
            raise NoStreamsError(self.url)

        self.logger.debug("URL={0}".format(hls_url))
        return {"live": HLSStream(self.session, hls_url)}


__plugin__ = QQ
