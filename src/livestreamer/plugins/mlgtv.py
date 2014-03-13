import re

from functools import partial

from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http
from livestreamer.stream import HDSStream, HLSStream
from livestreamer.utils import verifyjson


CONFIG_API_URL = "http://www.majorleaguegaming.com/player/config.json"
STREAM_API_URL = "http://streamapi.majorleaguegaming.com/service/streams/playback/{0}"
STREAM_ID_REGEX = r"<meta content='.+/([\w_-]+).+' property='og:video'>"
STREAM_TYPES = {
    "hls": partial(HLSStream.parse_variant_playlist, nameprefix="mobile_"),
    "hds": HDSStream.parse_manifest
}
URL_REGEX = r"http(s)?://(\w+\.)?(majorleaguegaming\.com|mlg\.tv)"


def valid_stream(stream):
    if not isinstance(stream, dict):
        return

    return stream.get("url") and stream.get("format") in STREAM_TYPES


class MLGTV(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return re.match(URL_REGEX, url)

    def _find_channel_id(self, text):
        match = re.search(STREAM_ID_REGEX, text)
        if match:
            return match.group(1)

    def _get_stream_id(self, channel_id):
        res = http.get(CONFIG_API_URL, params=dict(id=channel_id))
        config = http.json(res)
        media = verifyjson(config, "media")

        if not (media and isinstance(media, list)):
            return

        media = media[0]
        if not isinstance(media, dict):
            return

        return media.get("channel")

    def _get_streams(self):
        res = http.get(self.url)
        channel_id = self._find_channel_id(res.text)
        if not channel_id:
            return

        stream_id = self._get_stream_id(channel_id)
        if not stream_id:
            return

        res = http.get(STREAM_API_URL.format(stream_id),
                       params=dict(format="all"))
        json = http.json(res)
        data = verifyjson(json, "data")
        items = verifyjson(data, "items")

        streams = {}
        for stream in filter(valid_stream, items):
            parser = STREAM_TYPES[stream["format"]]

            try:
                streams.update(parser(self.session, stream["url"]))
            except IOError as err:
                if not re.search(r"(404|400) Client Error", str(err)):
                    self.logger.error("Failed to extract {0} streams: {1}",
                                      stream["format"].upper(), err)

        return streams

__plugin__ = MLGTV
