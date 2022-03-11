"""
$description Live TV channels from LTV, a Latvian public, state-owned broadcaster.
$url ltv.lsm.lv
$type live
$region Latvia
"""

import logging
import re
from urllib.parse import urlsplit, urlunsplit

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream, HLSStreamReader, HLSStreamWorker

log = logging.getLogger(__name__)


def copy_query_url(to, from_):
    """
    Replace the query string in one URL with the query string from another URL
    """
    return urlunsplit(urlsplit(to)._replace(query=urlsplit(from_).query))


class LTVHLSStreamWorker(HLSStreamWorker):
    def process_sequences(self, playlist, sequences):
        super().process_sequences(playlist, sequences)
        # update the segment URLs with the query string from the playlist URL
        self.playlist_sequences = [
            sequence._replace(
                segment=sequence.segment._replace(
                    uri=copy_query_url(sequence.segment.uri, self.stream.url)
                )
            )
            for sequence in self.playlist_sequences
        ]


class LTVHLSStreamReader(HLSStreamReader):
    __worker__ = LTVHLSStreamWorker


class LTVHLSStream(HLSStream):
    __reader__ = LTVHLSStreamReader

    @classmethod
    def parse_variant_playlist(cls, *args, **kwargs):
        streams = super().parse_variant_playlist(*args, **kwargs)

        for stream in streams.values():
            stream.args["url"] = copy_query_url(stream.args["url"], stream.url_master)

        return streams


@pluginmatcher(re.compile(
    r"https://ltv\.lsm\.lv/lv/tiesraide"
))
class LtvLsmLv(Plugin):
    """
    Support for Latvian live channels streams on ltv.lsm.lv
    """

    def __init__(self, url: str):
        super().__init__(url)
        self._json_data_re = re.compile(r'teliaPlayer\((\{.*?\})\);', re.DOTALL)

        self.main_page_schema = validate.Schema(
            validate.parse_html(),
            validate.xml_xpath_string(".//iframe[contains(@src, 'ltv.lsm.lv/embed')][1]/@src"),
            validate.url()
        )

        self.embed_code_schema = validate.Schema(
            validate.parse_html(),
            validate.xml_xpath_string(".//live[1]/@*[name()=':embed-data']"),
            str,
            validate.parse_json(),
            {"source": {"embed_code": str}},
            validate.get(("source", "embed_code")),
            validate.parse_html(),
            validate.xml_xpath_string(".//iframe[@src][1]/@src"),
        )

        self.player_apicall_schema = validate.Schema(
            validate.transform(self._json_data_re.search),
            validate.any(
                None,
                validate.all(
                    validate.get(1),
                    validate.transform(lambda s: s.replace("'", '"')),
                    validate.transform(lambda s: re.sub(r",\s*\}", "}", s, flags=re.DOTALL)),
                    validate.parse_json(),
                    {"channel": str},
                    validate.get("channel")
                )
            )
        )

        self.sources_schema = validate.Schema(
            validate.parse_json(),
            {
                "source": {
                    "sources": validate.all(
                        [{"type": str, "src": validate.url()}],
                        validate.filter(lambda src: src["type"] == "application/x-mpegURL"),
                        validate.map(lambda src: src.get("src"))
                    ),
                }},
            validate.get(("source", "sources"))
        )

    def _get_streams(self):
        api_url = "https://player.cloudycdn.services/player/ltvlive/channel/{channel_id}/"

        self.session.http.headers.update({"Referer": self.url})

        iframe_url = self.session.http.get(self.url, schema=self.main_page_schema)
        log.debug(f"Found embed iframe: {iframe_url}")
        player_iframe_url = self.session.http.get(iframe_url, schema=self.embed_code_schema)
        log.debug(f"Found player iframe: {player_iframe_url}")
        channel_id = self.session.http.get(player_iframe_url, schema=self.player_apicall_schema)
        log.debug(f"Found channel ID: {channel_id}")

        stream_sources = self.session.http.post(api_url.format(channel_id=channel_id),
                                                data=dict(refer="ltv.lsm.lv",
                                                          playertype="regular",
                                                          protocol="hls"),
                                                schema=self.sources_schema)
        for surl in stream_sources:
            yield from LTVHLSStream.parse_variant_playlist(self.session, surl).items()


__plugin__ = LtvLsmLv
