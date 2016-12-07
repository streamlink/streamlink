"""Plugin for Denmark's public service channel DR (Danmarks Radio)."""

import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import HLSStream, HDSStream

LIVE_CHANNELS_API_URL = "http://www.dr.dk/tv/external/channels?mediaType=tv"
VOD_API_URL = "http://www.dr.dk/mu/programcard/expanded/{0}"

STREAMING_TYPES = {
    "HDS": HDSStream.parse_manifest,
    "HLS": HLSStream.parse_variant_playlist
}

_url_re = re.compile(r"""
    http(s)?://(www\.)?dr.dk
    (?:
        /[TtVv]+/
        (?:
            live/(?P<channel>[^/]+)
        )?
        (?:
            se/(.+/)?(?P<program>[^/&?]+)
        )?
    )
""", re.VERBOSE)

_channels_schema = validate.Schema(
    {
        "Data": [{
            "Slug": validate.text,
            "StreamingServers": validate.all(
                [{
                    "LinkType": validate.text,
                    "Qualities": [
                        validate.all(
                            {
                                "Streams": validate.all(
                                    [
                                        validate.all(
                                            {"Stream": validate.text},
                                            validate.get("Stream")
                                        )
                                    ],
                                    validate.get(0)
                                )
                            },
                            validate.get("Streams")
                        )
                    ],
                    "Server": validate.text
                }],
                validate.filter(lambda s: s["LinkType"] in STREAMING_TYPES)
            )
        }]
    },
    validate.get("Data", {})
)

_video_schema = validate.Schema(
    { "Data": [{
        "Assets": validate.all(
            [{ validate.optional("Links"): validate.all(
                [{
                    "Target": validate.text,
                    "Uri": validate.text
                }],
                validate.filter(lambda l: l["Target"] in STREAMING_TYPES)
            )}],
            validate.filter(lambda a: "Links" in a)
        )
    }]},
    validate.get("Data", {}),
    validate.get(0, {}),
    validate.get("Assets", {}),
    validate.get(0, {}),
    validate.get("Links", []),
)


class DRDK(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_streams(self):
        match = _url_re.match(self.url)
        if not match:
            return

        if match.group("channel"):
            return self._get_live_streams(match.group("channel"))
        else:
            return self._get_vod_streams(match.group("program"))

    def _get_vod_streams(self, program):
        res = http.get(VOD_API_URL.format(program))
        video = http.json(res, schema=_video_schema)

        streams = {}
        for link in video:
            type = link["Target"]
            url = link["Uri"]
            parser = STREAMING_TYPES[type]

            try:
                streams.update(parser(self.session, url))
            except IOError as err:
                self.logger.error("Failed to load {0} streams: {1}", type, err)

        return streams

    def _get_live_streams(self, slug):
        res = http.get(LIVE_CHANNELS_API_URL)
        res = http.json(res, schema=_channels_schema)

        for channel in filter(lambda c: c["Slug"] == slug, res):
            servers = channel["StreamingServers"]
            return self._parse_streaming_servers(servers)

    def _parse_streaming_servers(self, servers):
        streams = {}
        for server in servers:
            type = server["LinkType"]
            base_url = server["Server"]
            qualities = server["Qualities"]
            parser = STREAMING_TYPES[type]

            for quality in qualities:
                try:
                    url = "{0}/{1}".format(base_url, quality)
                    streams.update(parser(self.session, url))
                except IOError as err:
                    self.logger.error("Failed to load {0} streams: {1}", type, err)

        return streams

__plugin__ = DRDK
