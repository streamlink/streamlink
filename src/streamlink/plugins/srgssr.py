from __future__ import print_function

import re

from streamlink import PluginError
from streamlink.compat import urlparse, parse_qsl, urlencode, urlunparse
from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream


class SRGSSR(Plugin):
    url_re = re.compile(r"""https?://(?:www\.)?
            (srf|rts|rsi|rtr)\.ch/
            (?:
                play/tv|
                livestream/player|
                live-streaming|
                sport/direct/(\d+)-
            )""", re.VERBOSE)
    api_url = "http://il.srgssr.ch/integrationlayer/1.0/ue/{site}/video/play/{id}.json"
    token_url = "http://tp.srgssr.ch/akahd/token"
    video_id_re = re.compile(r'urn(?:%3A|:)(srf|rts|rsi|rtr)(?:%3A|:)(?:ais(?:%3A|:))?video(?:%3A|:)([^&"]+)')
    video_id_schema = validate.Schema(validate.transform(video_id_re.search))
    api_schema = validate.Schema(
        {
            "Video":
                {
                    "Playlists":
                        {
                            "Playlist": [{
                                "@protocol": validate.text,
                                "url": [{"@quality": validate.text, "text": validate.url()}]
                            }]
                        }
                }
        },
        validate.get("Video"),
        validate.get("Playlists"),
        validate.get("Playlist"))
    token_schema = validate.Schema({"token": {"authparams": validate.text}},
                                   validate.get("token"),
                                   validate.get("authparams"))

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def get_video_id(self):
        parsed = urlparse(self.url)
        qinfo = dict(parse_qsl(parsed.query or parsed.fragment.lstrip("?")))

        site, video_id = None, None
        url_m = self.url_re.match(self.url)

        # look for the video id in the URL, otherwise find it in the page
        if "tvLiveId" in qinfo:
            video_id = qinfo["tvLiveId"]
            site = url_m.group(1)
        elif url_m.group(2):
            site, video_id = url_m.group(1), url_m.group(2)
        else:
            video_id_m = http.get(self.url, schema=self.video_id_schema)
            if video_id_m:
                site, video_id = video_id_m.groups()

        return site, video_id

    def auth_url(self, url):
        parsed = urlparse(url)
        path, _ = parsed.path.rsplit("/", 1)
        token_res = http.get(self.token_url, params=dict(acl=path + "/*"))
        authparams = http.json(token_res, schema=self.token_schema)

        existing = dict(parse_qsl(parsed.query))
        existing.update(dict(parse_qsl(authparams)))

        return urlunparse(parsed._replace(query=urlencode(existing)))

    def _get_streams(self):
        site, video_id = self.get_video_id()

        if video_id and site:
            self.logger.debug("Found {0} video ID {1}", site, video_id)

            try:
                res = http.get(self.api_url.format(site=site, id=video_id))
            except PluginError:
                return

            for stream_info in http.json(res, schema=self.api_schema):
                for url in stream_info["url"]:
                    if stream_info["@protocol"] == "HTTP-HLS":
                        for s in HLSStream.parse_variant_playlist(self.session, self.auth_url(url["text"])).items():
                            yield s


__plugin__ = SRGSSR
