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
            stream.args["url"] = copy_query_url(stream.args["url"], stream.multivariant.uri)

        return streams


@pluginmatcher(re.compile(
    r"https://ltv\.lsm\.lv/lv/tiesraide"
))
class LtvLsmLv(Plugin):
    URL_IFRAME = "https://ltv.lsm.lv/embed/live?c={embed_id}"
    URL_API = "https://player.cloudycdn.services/player/ltvlive/channel/{channel_id}/"

    def _get_streams(self):
        self.session.http.headers.update({"Referer": self.url})

        embed_id = self.session.http.get(self.url, schema=validate.Schema(
            re.compile(r"""embed_id\s*:\s*(?P<q>")(?P<embed_id>\w+)(?P=q)"""),
            validate.any(None, validate.get("embed_id")),
        ))
        if not embed_id:
            return
        log.debug(f"Found embed ID: {embed_id}")

        iframe_url = self.URL_IFRAME.format(embed_id=embed_id)
        starts_at, channel_id = self.session.http.get(iframe_url, schema=validate.Schema(
            validate.parse_html(),
            validate.xml_xpath_string(".//live[1]/@*[name()=':embed-data']"),
            str,
            validate.parse_json(),
            {
                "parentInfo": {"starts_at": validate.any(None, str)},
                "source": {"item_id": str},
            },
            validate.union_get(
                ("parentInfo", "starts_at"),
                ("source", "item_id"),
            ),
        ))
        if channel_id is None:
            return
        log.debug(f"Found channel ID: {channel_id}")

        if starts_at is not None:
            log.error(f"Stream starts at {starts_at}")
            return

        stream_sources = self.session.http.post(
            self.URL_API.format(channel_id=channel_id),
            data={
                "refer": "ltv.lsm.lv",
                "playertype": "regular",
                "protocol": "hls",
            },
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "source": {
                        "sources": validate.all(
                            [{"type": str, "src": validate.url()}],
                            validate.filter(lambda src: src["type"] == "application/x-mpegURL"),
                            validate.map(lambda src: src.get("src")),
                        ),
                    },
                },
                validate.get(("source", "sources")),
            ),
        )
        for surl in stream_sources:
            yield from LTVHLSStream.parse_variant_playlist(self.session, surl).items()


__plugin__ = LtvLsmLv
