import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HTTPStream
from streamlink import NoStreamsError


class Tamago(Plugin):

    _url_re = re.compile(r"https?://(?:player\.)?tamago\.live/w/(?P<id>\d+)")

    _api_url_base = "https://player.tamago.live/api/rooms/{id}"

    _api_response_schema = validate.Schema({
        u"status": 200,
        u"message": u"Success",
        u"data": {
            u"room_number": validate.text,
            u"stream": {validate.text: validate.url()}
        }
    })

    _stream_qualities = {
        u"150": "144p",
        u"350": "360p",
        u"550": "540p",
        u"900": "720p",
    }

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_streams(self):
        user_id = self._url_re.match(self.url).group('id')

        try:
            api_response = self.session.http.get(self._api_url_base.format(id=user_id))
            streams = self.session.http.json(api_response, schema=self._api_response_schema)['data']['stream']
        except Exception:
            raise NoStreamsError(self.url)

        unique_stream_urls = []
        for stream in streams.keys():
            if streams[stream] not in unique_stream_urls:
                unique_stream_urls.append(streams[stream])
                quality = self._stream_qualities[stream] if stream in self._stream_qualities.keys() else "720p+"
                yield quality, HTTPStream(self.session, streams[stream])


__plugin__ = Tamago
