from livestreamer.plugin import Plugin
from livestreamer.stream import HDSStream, HLSStream
from livestreamer.utils import res_json, verifyjson, urlget

import re

CONFIG_URL = "http://www.majorleaguegaming.com/player/config.json"
STREAM_ID_REGEX = r"<meta content='.+/([\w_-]+).+' property='og:video'>"
URL_REGEX = r"http(s)?://(\w+\.)?(majorleaguegaming\.com|mlg\.tv)"


class MLGTV(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return re.match(URL_REGEX, url)

    def _find_stream_id(self, text):
        match = re.search(STREAM_ID_REGEX, text)
        if match:
            return match.group(1)

    def _get_streams(self):
        res = urlget(self.url)
        stream_id = self._find_stream_id(res.text)

        if not stream_id:
            return

        return self._get_streams_from_id(stream_id)

    def _get_streams_from_id(self, stream_id):
        res = urlget(CONFIG_URL, params=dict(id=stream_id))
        config = res_json(res)
        media = verifyjson(config, "media")

        if not (media and isinstance(media, list)):
            return

        streams = {}
        media = media[0]
        hds_manifest = media.get("name")
        hls_manifest = media.get("hlsUrl")

        if hds_manifest:
            try:
                hds_streams = HDSStream.parse_manifest(self.session,
                                                       hds_manifest)
                streams.update(hds_streams)
            except IOError as err:
                if not re.search(r"(404|400) Client Error", str(err)):
                    self.logger.error("Failed to parse HDS manifest: {0}", err)

        if hls_manifest:
            try:
                hls_streams = HLSStream.parse_variant_playlist(self.session,
                                                               hls_manifest,
                                                               nameprefix="mobile_")
                streams.update(hls_streams)
            except IOError as err:
                if not re.search(r"(404|400) Client Error", str(err)):
                    self.logger.error("Failed to parse HLS playlist: {0}", err)

        return streams

__plugin__ = MLGTV
