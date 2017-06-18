"""Plugin for swedish news paper Aftonbladet's streaming service."""

import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import HDSStream, HLSStream

PLAYLIST_URL_FORMAT = "http://{address}/{path}/{filename}"
STREAM_TYPES = {
    "hds": HDSStream.parse_manifest,
    "hls": HLSStream.parse_variant_playlist
}
STREAM_FORMATS = ("m3u8", "f4m")
VIDEO_INFO_URL = "http://aftonbladet-play-static-ext.cdn.drvideo.aptoma.no/actions/video"
METADATA_URL = "http://aftonbladet-play-metadata.cdn.drvideo.aptoma.no/video/{0}.json"

_embed_re = re.compile(r"<iframe src=\"(http://tv.aftonbladet.se[^\"]+)\"")
_aptoma_id_re = re.compile(r"<div id=\"drvideo\".+data-aptomaId=\"([^\"]+)\"")
_live_re = re.compile(r"data-isLive=\"true\"")
_url_re = re.compile(r"http(s)?://(\w+.)?.aftonbladet.se")

_video_schema = validate.Schema(
    {
        "formats": validate.all(
            {
                validate.text: {
                    validate.text: validate.all(
                        dict,
                        validate.filter(lambda k, v: k in STREAM_FORMATS),
                        {
                            validate.text: [{
                                "address": validate.text,
                                "filename": validate.text,
                                "path": validate.text
                            }]
                        },
                    )
                }
            },
            validate.filter(lambda k, v: k in STREAM_TYPES)
        )
    }
)


class Aftonbladet(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_streams(self):
        res = http.get(self.url)
        match = _embed_re.search(res.text)
        if match:
            res = http.get(match.group(1))

        match = _aptoma_id_re.search(res.text)
        if not match:
            return

        aptoma_id = match.group(1)
        if not _live_re.search(res.text):
            res = http.get(METADATA_URL.format(aptoma_id))
            metadata = http.json(res)
            video_id = metadata["videoId"]
        else:
            video_id = aptoma_id

        res = http.get(VIDEO_INFO_URL, params=dict(id=video_id))
        video = http.json(res, schema=_video_schema)
        streams = {}
        for fmt, providers in video["formats"].items():
            for name, provider in providers.items():
                for ext, playlists in provider.items():
                    for playlist in playlists:
                        url = PLAYLIST_URL_FORMAT.format(**playlist)
                        parser = STREAM_TYPES[fmt]

                        try:
                            streams.update(parser(self.session, url))
                        except IOError as err:
                            self.logger.error("Failed to extract {0} streams: {1}",
                                              fmt.upper(), err)

        return streams


__plugin__ = Aftonbladet
