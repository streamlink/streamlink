"""Plugin for DOMMUNE, simply extracts current live YouTube stream."""

import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate

DATA_URL = "http://www.dommune.com/freedommunezero2012/live/data/data.json"

_url_re = re.compile(r"http(s)?://(\w+\.)?dommune.com")
_data_schema = validate.Schema({
    "channel": validate.text,
    "channel2": validate.text
})


class Dommune(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_streams(self):
        res = http.get(DATA_URL)
        data = http.json(res, schema=_data_schema)
        video_id = data["channel"] or data["channel2"]
        if not video_id:
            return

        url = "http://youtu.be/{0}".format(video_id)
        return self.session.streams(url)


__plugin__ = Dommune
