# -*- coding: utf-8 -*-
import re

from streamlink.exceptions import NoStreamsError
from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HTTPStream


class Kugou(Plugin):
    """ Streamlink plugin for fanxing.kugou.com """

    _url_re = re.compile(r"""https?://fanxing.kugou.com/(?P<room_id>\d+)""")

    _room_stream_list_schema = validate.Schema(
        {
            "data": validate.any(None, {
                "httpflv": validate.url()
            })
        },
        validate.get("httpflv_room_stream_list_schema")
    )

    _api_url = 'https://fx2.service.kugou.com/video/pc/live/pull/v3/streamaddr?ch=fx&version=1.0&streamType=2&ua=fx-flash&kugouId=0&roomId={}'

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url)

    
    def _get_streams(self):
        match = self._url_re.match(self.url)
        if not match:
            return
        
        room_id = match.group('room_id')

        res = self.session.http.get(self._api_url.format(room_id))

        stream_data_json = self.session.http.json(res)

        if stream_data_json["code"] != 0 or stream_data_json["data"]["status"] != 1:
            return 

        horizontal = stream_data_json["data"]["horizontal"]
        vertical = stream_data_json["data"]["vertical"]

        try:
            if len(horizontal) == 0:
                flv_url = vertical[0]["httpflv"][0]
            else:
                flv_url = horizontal[0]["httpflv"][0]
        except Exception as e:
            raise NoStreamsError(self.url)

        self.logger.debug("URL = {}".format(flv_url))
        return {"live": HTTPStream(self.session, flv_url)}


__plugin__ = Kugou