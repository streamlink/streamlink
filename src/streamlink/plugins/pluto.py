"""
$description Live TV and video on-demand service owned by Paramount Streaming.
$url pluto.tv
$type live, vod
"""

import logging
import re
from urllib.parse import parse_qs, urljoin
from uuid import uuid4

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream, HLSStreamReader, HLSStreamWriter
from streamlink.utils.url import update_qsd


log = logging.getLogger(__name__)


class PlutoHLSStreamWriter(HLSStreamWriter):
    ad_re = re.compile(r"_ad/creative/|dai\.google\.com|Pluto_TV_OandO/.*Bumper")

    def should_filter_sequence(self, sequence):
        return self.ad_re.search(sequence.segment.uri) is not None or super().should_filter_sequence(sequence)


class PlutoHLSStreamReader(HLSStreamReader):
    __writer__ = PlutoHLSStreamWriter


class PlutoHLSStream(HLSStream):
    __shortname__ = "hls-pluto"
    __reader__ = PlutoHLSStreamReader


@pluginmatcher(re.compile(r"""
    https?://(?:www\.)?pluto\.tv/(?:\w{2}/)?(?:
        live-tv/(?P<slug_live>[^/]+)
        |
        on-demand/series/(?P<slug_series>[^/]+)(?:/season/\d+)?/episode/(?P<slug_episode>[^/]+)
        |
        on-demand/movies/(?P<slug_movies>[^/]+)
    )/?$
""", re.VERBOSE))
class Pluto(Plugin):
    def _get_api_data(self, kind, slug, slugfilter=None):
        log.debug(f"slug={slug}")
        app_version = self.session.http.get(self.url, schema=validate.Schema(
            validate.parse_html(),
            validate.xml_xpath_string(".//head/meta[@name='appVersion']/@content"),
            validate.any(None, str),
        ))
        if not app_version:
            return

        log.debug(f"app_version={app_version}")

        return self.session.http.get(
            "https://boot.pluto.tv/v4/start",
            params={
                "appName": "web",
                "appVersion": app_version,
                "deviceVersion": "94.0.0",
                "deviceModel": "web",
                "deviceMake": "firefox",
                "deviceType": "web",
                "clientID": str(uuid4()),
                "clientModelNumber": "1.0",
                kind: slug,
            },
            schema=validate.Schema(
                validate.parse_json(), {
                    "servers": {
                        "stitcher": validate.url(),
                    },
                    validate.optional("EPG"): [{
                        "name": str,
                        "id": str,
                        "slug": str,
                        "stitched": {
                            "path": str,
                        },
                    }],
                    validate.optional("VOD"): [{
                        "name": str,
                        "id": str,
                        "slug": str,
                        "genre": str,
                        "stitched": {
                            "path": str,
                        },
                        validate.optional("seasons"): [{
                            "episodes": validate.all(
                                [{
                                    "name": str,
                                    "_id": str,
                                    "slug": str,
                                    "stitched": {
                                        "path": str,
                                    },
                                }],
                                validate.filter(lambda k: slugfilter and k["slug"] == slugfilter),
                            ),
                        }],
                    }],
                    "sessionToken": str,
                    "stitcherParams": str,
                },
            ),
        )

    def _get_playlist(self, host, path, params, token):
        qs = parse_qs(params)
        qs["jwt"] = token
        yield from PlutoHLSStream.parse_variant_playlist(self.session, update_qsd(urljoin(host, path), qs)).items()

    @staticmethod
    def _get_media_data(data, key, slug):
        media = data.get(key)
        if media and media[0]["slug"] == slug:
            return media[0]

    def _get_streams(self):
        m = self.match.groupdict()
        if m["slug_live"]:
            data = self._get_api_data("channelSlug", m["slug_live"])
            media = self._get_media_data(data, "EPG", m["slug_live"])
            if not media:
                return

            self.id = media["id"]
            self.title = media["name"]
            path = media["stitched"]["path"]

        elif m["slug_series"] and m["slug_episode"]:
            data = self._get_api_data("episodeSlugs", m["slug_series"], slugfilter=m["slug_episode"])
            media = self._get_media_data(data, "VOD", m["slug_series"])
            if not media or "seasons" not in media:
                return

            for season in media["seasons"]:
                if season["episodes"]:
                    episode = season["episodes"][0]
                    if episode["slug"] == m["slug_episode"]:
                        break
            else:
                return

            self.author = media["name"]
            self.category = media["genre"]
            self.id = episode["_id"]
            self.title = episode["name"]
            path = episode["stitched"]["path"]

        elif m["slug_movies"]:
            data = self._get_api_data("episodeSlugs", m["slug_movies"])
            media = self._get_media_data(data, "VOD", m["slug_movies"])
            if not media:
                return

            self.category = media["genre"]
            self.id = media["id"]
            self.title = media["name"]
            path = media["stitched"]["path"]

        else:
            return

        log.trace(f"data={data!r}")
        log.debug(f"path={path}")

        return self._get_playlist(
            data["servers"]["stitcher"],
            path,
            data["stitcherParams"],
            data["sessionToken"],
        )


__plugin__ = Pluto
