"""
$description Live TV and video on-demand service owned by Paramount Streaming.
$url pluto.tv
$type live, vod
$metadata id
$metadata author
$metadata category
$metadata title
"""

import logging
import re
from urllib.parse import parse_qsl, urljoin
from uuid import uuid4

from streamlink.exceptions import PluginError
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import useragents, validate
from streamlink.stream.hls import HLSStream, HLSStreamReader, HLSStreamWriter
from streamlink.utils.url import update_qsd


log = logging.getLogger(__name__)


class PlutoHLSStreamWriter(HLSStreamWriter):
    ad_re = re.compile(r"_ad/creative/|creative/\d+_ad/|dai\.google\.com|Pluto_TV_OandO/.*(Bumper|plutotv_filler)")

    def should_filter_segment(self, segment):
        return self.ad_re.search(segment.uri) is not None or super().should_filter_segment(segment)


class PlutoHLSStreamReader(HLSStreamReader):
    __writer__ = PlutoHLSStreamWriter


class PlutoHLSStream(HLSStream):
    __shortname__ = "hls-pluto"
    __reader__ = PlutoHLSStreamReader


@pluginmatcher(
    name="live",
    pattern=re.compile(
        r"https?://(?:www\.)?pluto\.tv/(?:\w{2}/)?live-tv/(?P<id>[^/]+)/?$",
    ),
)
@pluginmatcher(
    name="series",
    pattern=re.compile(
        r"https?://(?:www\.)?pluto\.tv/(?:\w{2}/)?on-demand/series/(?P<id_s>[^/]+)(?:/season/\d+)?/episode/(?P<id_e>[^/]+)/?$",
    ),
)
@pluginmatcher(
    name="movies",
    pattern=re.compile(
        r"https?://(?:www\.)?pluto\.tv/(?:\w{2}/)?on-demand/movies/(?P<id>[^/]+)/?$",
    ),
)
class Pluto(Plugin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session.http.headers.update({"User-Agent": useragents.FIREFOX})
        self._app_version = None
        self._device_version = re.search(r"Firefox/(\d+(?:\.\d+)*)", useragents.FIREFOX)[1]
        self._client_id = str(uuid4())

    @property
    def app_version(self):
        if self._app_version:
            return self._app_version

        self._app_version = self.session.http.get(
            self.url,
            schema=validate.Schema(
                validate.parse_html(),
                validate.xml_xpath_string(".//head/meta[@name='appVersion']/@content"),
                validate.any(None, str),
            ),
        )
        if not self._app_version:
            raise PluginError("Could not find pluto app version")

        log.debug(f"{self._app_version=}")

        return self._app_version

    def _get_api_data(self, request):
        log.debug(f"_get_api_data: {request=}")

        schema_paths = validate.any(
            validate.all(
                {
                    "paths": [
                        validate.all(
                            {
                                "type": str,
                                "path": str,
                            },
                            validate.union_get("type", "path"),
                        ),
                    ],
                },
                validate.get("paths"),
            ),
            validate.all(
                {
                    "path": str,
                },
                validate.transform(lambda obj: [("hls", obj["path"])]),
            ),
        )
        schema_live = [
            {
                "name": str,
                "id": str,
                "slug": str,
                "stitched": schema_paths,
            },
        ]
        schema_vod = [
            {
                "name": str,
                "id": str,
                "slug": str,
                "genre": str,
                "stitched": validate.any(schema_paths, {}),
                validate.optional("seasons"): [
                    {
                        "episodes": [
                            {
                                "name": str,
                                "_id": str,
                                "slug": str,
                                "stitched": schema_paths,
                            },
                        ],
                    },
                ],
            },
        ]

        return self.session.http.get(
            "https://boot.pluto.tv/v4/start",
            params={
                "appName": "web",
                "appVersion": self.app_version,
                "deviceVersion": self._device_version,
                "deviceModel": "web",
                "deviceMake": "firefox",
                "deviceType": "web",
                "clientID": self._client_id,
                "clientModelNumber": "1.0.0",
                **request,
            },
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "servers": {
                        "stitcher": validate.url(),
                    },
                    "stitcherParams": str,
                    "sessionToken": str,
                    validate.optional("EPG"): schema_live,
                    validate.optional("VOD"): schema_vod,
                },
            ),
        )

    def _get_streams_live(self):
        data = self._get_api_data({"channelSlug": self.match["id"]})
        epg = data.get("EPG", [])
        media = next((e for e in epg if e["id"] == self.match["id"]), None)
        if not media:
            return

        self.id = media["id"]
        self.title = media["name"]

        return data, media["stitched"]

    def _get_streams_series(self):
        data = self._get_api_data({"seriesIDs": self.match["id_s"]})
        vod = data.get("VOD", [])
        media = next((v for v in vod if v["id"] == self.match["id_s"]), None)
        if not media:
            return
        seasons = media.get("seasons", [])
        episode = next((e for s in seasons for e in s["episodes"] if e["_id"] == self.match["id_e"]), None)
        if not episode:
            return

        self.id = episode["_id"]
        self.author = media["name"]
        self.category = media["genre"]
        self.title = episode["name"]

        return data, episode["stitched"]

    def _get_streams_movies(self):
        data = self._get_api_data({"seriesIDs": self.match["id"]})
        vod = data.get("VOD", [])
        media = next((v for v in vod if v["id"] == self.match["id"]), None)
        if not media:
            return

        self.id = media["id"]
        self.category = media["genre"]
        self.title = media["name"]

        return data, media["stitched"]

    def _get_streams(self):
        res = None
        if self.matches["live"]:
            res = self._get_streams_live()
        elif self.matches["series"]:
            res = self._get_streams_series()
        elif self.matches["movies"]:
            res = self._get_streams_movies()

        if not res:
            return

        data, paths = res
        for mediatype, path in paths:
            if mediatype != "hls":
                continue

            params = dict(parse_qsl(data["stitcherParams"]))
            params["jwt"] = data["sessionToken"]
            url = urljoin(data["servers"]["stitcher"], path)
            url = update_qsd(url, params)

            return PlutoHLSStream.parse_variant_playlist(self.session, url)


__plugin__ = Pluto
