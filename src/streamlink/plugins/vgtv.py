"""Plugin for VGTV, Norwegian newspaper VG Nett's streaming service."""

import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import HDSStream, HLSStream, HTTPStream

# This will have to be set to handle "secure" HDS streams. For now we
# leave it empty, as the same streams can likely be watched with HLS.
# SWF_URL = ""
STREAM_TYPES = {
    "hds": {
        "parser": HDSStream.parse_manifest,
#         "params": { "pvswf": SWF_URL },
        "file": "manifest.f4m"
    },
    "hls": {
        "parser": HLSStream.parse_variant_playlist,
        "file" : "master.m3u8"
    },
    "http" : {}
}

# For now we only handle MP4.
STREAM_FORMATS = ("mp4")

INFO_URL = "http://www.vgtv.no/data/actions/videostatus/"

_url_re = re.compile("https?://(www\.)?(vgtv|vg).no")
_content_id_re = re.compile("(?:data-videoid=\"|videostatus/\?id=)(\d+)")
_url_id_re = re.compile((
    "https?://(?:www\.)?vgtv.no/"
    "(?:(?:#!/)?video/|(?:#!|\?)id=)(\d+)"
))

_video_schema = validate.Schema({
    "status": 200,
    "formats": validate.all(
        dict,
        validate.filter(lambda k, v: k in STREAM_TYPES),
        {
            validate.text: validate.all(
                dict,
                validate.filter(lambda k, v: k in STREAM_FORMATS),
                {
                    validate.text: [{
                        "bitrate" : int,
                        "paths": [{
                            "address": validate.text,
                            "port" : int,
                            "path" : validate.text,
                            "filename": validate.text,
                            "application": validate.text,
                        }],
                    }]
                }
            )
        }
    )
})

class VGTV(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    def _build_url(self, **kwargs):
        kwargs["scheme"] = "https" if kwargs["port"] == 443 else "http"
        return "{scheme}://{address}:{port}/{path}".format(**kwargs)

    def _get_streams(self):
        match = _url_id_re.search(self.url)

        video_id = None

        # We can get the VGTV ID directly from vgtv.no URLs
        if match:
            video_id = match.group(1)

        # If we can't, we need to get the VGTV ID from the page content
        else:
            res = http.get(self.url)
            match = _content_id_re.search(res.text)
            if match:
                video_id = match.group(1)

        if not video_id:
            return

        # Now fetch video information
        self.logger.debug("Fetching video info for ID {0}", video_id)
        res = http.get(INFO_URL, params=dict(id=video_id))
        info = http.json(res, schema=_video_schema)

        streams = {}

        # At the time of writing, The previously fetched JSON doesn't
        # point to playlist/manifest files, but to individual stream
        # variants. Based on the provided variants, however, we can
        # build the playlist URLs ourselves.

        # HDS/HLS: Get all variants and produce a playlist URL.
        for f in ('hds', 'hls'):
            if not f in info["formats"]:
                next

            if not "mp4" in info["formats"][f]:
                next

            streamtype = STREAM_TYPES[f]
            f_streams = {}
            hmac = ""

            # Get variants.
            for stream in info["formats"][f]["mp4"]:
                for p in stream["paths"]:
                    url = self._build_url(**p)
                    variant = p["filename"][:-4] # strip ".mp4"

                    if url in f_streams:
                        f_streams[url].append(variant)
                    else:
                        f_streams[url] = [variant]

                    if p["application"]:
                        hmac = "?hdnea={0}&hdcore?3.1.0".format(
                            p["application"]
                        )

            # Make playlist URL and pass to parser.
            for url, variants in f_streams.items():
                playlist = "{0}/,{1},.mp4.csmil/{2}{3}".format(
                    url,
                    ",".join(variants),
                    streamtype["file"],
                    hmac
                )
                parser = streamtype["parser"]
                params = streamtype.get("params") or {}

                try:
                    streams.update(parser(self.session, playlist, **params))
                except IOError as err:
                    self.logger.error("Failed to extract {0} streams: {1}",
                                      f.upper(), err)

        # HTTP: Also make direct content URLs available for use.
        http_formats = info["formats"].get("http")
        if http_formats and "mp4" in http_formats:
            for stream in http_formats["mp4"]:
                p = stream["paths"][0]
                url = "{0}/{1}".format(self._build_url(**p), p["filename"])
                stream_name = "http_{0}k".format(stream["bitrate"])
                streams[stream_name] = HTTPStream(self.session, url)

        return streams

__plugin__ = VGTV
