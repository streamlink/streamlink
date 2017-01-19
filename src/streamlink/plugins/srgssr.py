from __future__ import print_function
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.plugin.api import validate
from streamlink.stream import HDSStream
from streamlink.stream import HLSStream
from streamlink.compat import urlparse, parse_qsl


class SRGSSR(Plugin):
    url_re = re.compile(r"https?://(?:www\.)?(srf|rts|rsi|rtr)\.ch/play/tv")
    api_url = "http://il.srgssr.ch/integrationlayer/1.0/ue/{site}/video/play/{id}.json"
    video_id_re = re.compile(r'urn:(srf|rts|rsi|rtr):(?:ais:)?video:([^&"]+)')
    video_id_schema = validate.Schema(validate.transform(video_id_re.search))
    api_schema = validate.Schema(
        {"Video":
            {"Playlists":
                {"Playlist": [{
                    "@protocol": validate.text,
                    "url": [{"@quality": validate.text, "text": validate.url()}]
                }]
                }
            }
        },
        validate.get("Video"),
        validate.get("Playlists"),
        validate.get("Playlist"))

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def get_video_id(self):
        parsed = urlparse(self.url)
        qinfo = dict(parse_qsl(parsed.query or parsed.fragment.lstrip("?")))

        site, video_id = None, None

        # look for the video id in the URL, otherwise find it in the page
        if "tvLiveId" in qinfo:
            video_id = qinfo["tvLiveId"]
            site = self.url_re.match(self.url).group(1)
        else:
            video_id_m = http.get(self.url, schema=self.video_id_schema)
            if video_id_m:
                site, video_id = video_id_m.groups()

        return site, video_id

    def _get_streams(self):
        video_id, site = self.get_video_id()

        if video_id and site:
            self.logger.debug("Found {0} video ID {1}", site, video_id)

            res = http.get(self.api_url.format(site=site, id=video_id))

            for stream_info in http.json(res, schema=self.api_schema):
                for url in stream_info["url"]:
                    if stream_info["@protocol"] == "HTTP-HDS":
                        for s in HDSStream.parse_manifest(self.session, url["text"]).items():
                            yield s
                    if stream_info["@protocol"] == "HTTP-HLS":
                        for s in HLSStream.parse_variant_playlist(self.session, url["text"]).items():
                            yield s


__plugin__ = SRGSSR
