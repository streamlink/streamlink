"""
$description Live TV channels and video on-demand service from TV Azteca, a Mexican free-to-air broadcaster.
$url tvazteca.com
$url adn40.mx
$type live, vod
$region Mexico
"""

import re
from dataclasses import asdict, dataclass
from urllib.parse import urlencode, urlparse

from streamlink import PluginError
from streamlink.logger import getLogger
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream
from streamlink.utils.url import url_concat


log = getLogger(__name__)


@dataclass
class SafeModeTokenRequest:
    asset_id: str
    type: str
    token: str


@dataclass
class TVAztecaPage:
    video_id: str
    embed_url: str
    title: str | None = None
    channel: str | None = None
    program: str | None = None


@dataclass
class EnVivoConfig:
    client_id: str
    player_id: str
    app_version: str


@dataclass
class EnVivoPageMedia:
    id: str
    title: str
    purchased: int


@dataclass
class EnVivoMedia:
    id: str
    title: str
    access_token: str
    channel: str | None = None
    program: str | None = None


@dataclass
class EnVivoPlayback:
    hls_url: str
    uid: str
    sid: str
    pid: str


@pluginmatcher(
    name="tvazteca",
    pattern=re.compile(
        r"https?://(?:www\.)?tvazteca\.com/(?P<path>\S+?)/?$",
    ),
)
@pluginmatcher(
    name="adn40",
    pattern=re.compile(
        r"https?://(?:www|live)\.adn40\.mx(?:/(?P<path>\S*))?$",
    ),
)
@pluginmatcher(
    name="envivo_live",
    pattern=re.compile(
        r"https?://envivo\.tvazteca\.com/watch/live/(?P<id>[^/?#]+)/?$",
    ),
)
@pluginmatcher(
    name="envivo_vod",
    pattern=re.compile(
        r"https?://envivo\.tvazteca\.com/watch/media/(?P<id>[^/?#]+)/?$",
    ),
)
class TVAzteca(Plugin):
    _ENVIVO_DOMAIN = "envivo.tvazteca.com"
    _ENVIVO_ORIGIN = f"https://{_ENVIVO_DOMAIN}"
    _ENVIVO_REFERER = f"https://{_ENVIVO_DOMAIN}/"
    _ENVIVO_LIVE_QUERY = """
    query getPlayerLive($id: String!) {
      getLive(_id: $id) {
        _id
        name
        accessToken
        schedules {
          name
          current
        }
      }
    }
    """
    _ENVIVO_MEDIA_QUERY = """
    query getPlayerMedia($id: String!) {
      getMedia(_id: $id) {
        _id
        title
        accessToken
      }
    }
    """
    _ENVIVO_PAGE_MEDIA_QUERY = """
    query getPlayerPageMedia($id: String!) {
      getMedia(_id: $id) {
        _id
        title
        purchased
      }
    }
    """

    _ENVIVO_APP_NAME = "tv-azteca-en-vivo-app-web"
    _ENVIVO_DEFAULT_RESOLUTION = "1920x1080"

    _MDSTRM_ENDPOINT_ENVIVO_LIVE = "live-stream"
    _MDSTRM_ENDPOINT_ENVIVO_VOD = "video"

    _SCHEMA_PLAYER = validate.Schema(
        validate.xml_xpath(
            ".//div[@data-video-player][@data-video-id][@data-player-id][@data-video-type][1]",
        ),
        validate.none_or_all(
            validate.get(0),
            validate.union((
                validate.get("data-video-id"),
                validate.get("data-player-id"),
                validate.get("data-video-type"),
                validate.get("data-video-title"),
                validate.get("data-video-channel"),
                validate.get("data-video-program"),
                validate.all(
                    validate.get("data-safe-mode-config"),
                    validate.none_or_all(
                        validate.parse_json(),
                        {
                            "domain": str,
                            "bodyJson": validate.all(
                                str,
                                validate.parse_json(),
                                {
                                    "asset_id": str,
                                    "type": str,
                                    "token": str,
                                },
                                validate.union_get("asset_id", "type", "token"),
                            ),
                        },
                        validate.union_get("domain", "bodyJson"),
                    ),
                ),
            )),
        ),
    )
    _SCHEMA_SCRIPT = validate.Schema(
        validate.xml_xpath(".//script[@type='application/ld+json'][contains(text(),'VideoObject')]/text()"),
        validate.none_or_all(
            [
                validate.all(
                    validate.parse_json(),
                    validate.any(
                        list,
                        validate.transform(lambda obj: [obj]),
                    ),
                    [dict],
                    validate.filter(lambda obj: obj.get("@type", "") == "VideoObject"),
                    validate.get(0),
                    validate.none_or_all(
                        {
                            "embedUrl": validate.url(
                                hostname="mdstrm.com",
                            ),
                            "name": validate.any(None, str),
                            "mainEntityOfPage": {
                                "publisher": {
                                    "name": validate.any(None, str),
                                },
                            },
                        },
                        validate.union_get(
                            "embedUrl",
                            "name",
                            ("mainEntityOfPage", "publisher", "name"),
                        ),
                    ),
                ),
            ],
            validate.filter(bool),
            validate.get(0),
        ),
    )
    _SCHEMA_ADN_METADATA = validate.Schema(
        validate.union((
            validate.xml_xpath_string(
                ".//h1[contains(concat(' ', normalize-space(@class), ' '), ' b-adn-live-schedule__program-title ')][1]/text()",
            ),
            validate.xml_xpath_string(
                ".//meta[@name='datalayer-videotitle'][1]/@content",
            ),
        )),
    )
    _SCHEMA_FUSION_PLAYER = validate.Schema(
        validate.xml_xpath(
            ".//script[@id='fusion-metadata'][contains(text(),'Fusion.tree')][1]/text()",
        ),
        validate.none_or_all(
            validate.get(0),
            re.compile(r"Fusion\.tree\s*=\s*(?P<json>\{.+?});", re.DOTALL),
            validate.none_or_all(
                validate.get("json"),
                validate.parse_json(),
                {
                    "children": [
                        validate.all(
                            {
                                "children": [
                                    {
                                        "type": str,
                                        "props": dict,
                                    },
                                ],
                            },
                            validate.get("children"),
                            validate.filter(lambda obj: obj["type"] == "tva-mediastream-block/default"),
                            validate.get(0),
                            validate.none_or_all(
                                {
                                    "props": {
                                        "customFields": {
                                            "videoId": str,
                                            "playerId": str,
                                            "videoType": str,
                                        },
                                    },
                                },
                                validate.union_get(
                                    ("props", "customFields", "videoId"),
                                    ("props", "customFields", "playerId"),
                                    ("props", "customFields", "videoType"),
                                ),
                            ),
                        ),
                    ],
                },
                validate.get("children"),
                validate.filter(bool),
                validate.get(0),
            ),
        ),
    )

    def _get_streams(self):
        if self.matches["tvazteca"] or self.matches["adn40"]:
            return self._get_tvazteca_streams()
        elif self.matches["envivo_live"]:
            return self._get_envivo_streams(self._MDSTRM_ENDPOINT_ENVIVO_LIVE)
        elif self.matches["envivo_vod"]:
            return self._get_envivo_streams(self._MDSTRM_ENDPOINT_ENVIVO_VOD)

    # tvazteca/adn40
    def _get_tvazteca_streams(self):
        page = self._get_tvazteca_page()

        log.debug(f"Video ID: {page.video_id}")
        log.debug(f"Embed URL: {page.embed_url}")

        streams = self.session.streams(page.embed_url)

        self.id = page.video_id
        self.title = page.title
        self.author = page.channel
        self.category = page.program

        return streams

    def _get_tvazteca_page(self) -> TVAztecaPage:
        root = self.session.http.get(
            self.url,
            schema=validate.Schema(validate.parse_html()),
        )

        # www.tvazteca.com live/video
        if player := self._SCHEMA_PLAYER.validate(root):
            video_id, player_id, video_type, title, channel, program, safe_mode = player

            access_token = None
            if safe_mode:
                domain, (asset_id, token_type, token) = safe_mode
                access_token = self._request_access_token(
                    domain,
                    SafeModeTokenRequest(
                        asset_id=asset_id,
                        type=token_type,
                        token=token,
                    ),
                )

            return TVAztecaPage(
                video_id=video_id,
                embed_url=self._get_mdstrm_url(
                    video_id,
                    player_id,
                    video_type,
                    access_token,
                ),
                title=title,
                channel=channel,
                program=program,
            )

        # adn40 live
        if player := self._SCHEMA_FUSION_PLAYER.validate(root):
            video_id, player_id, video_type = player
            title, channel = self._SCHEMA_ADN_METADATA.validate(root)

            return TVAztecaPage(
                video_id=video_id,
                embed_url=self._get_mdstrm_url(
                    video_id,
                    player_id,
                    video_type,
                ),
                title=title,
                channel=channel,
            )

        # adn40 video
        if script := self._SCHEMA_SCRIPT.validate(root):
            embed_url, title, channel = script
            path = urlparse(embed_url).path.rstrip("/")

            if not path:
                raise PluginError(f"Invalid MDStrm embed URL: {embed_url}")

            return TVAztecaPage(
                video_id=path.rsplit("/", 1)[-1],
                embed_url=embed_url,
                title=title,
                channel=channel,
            )

        raise PluginError("Unable to locate video metadata")

    def _request_access_token(
        self,
        token_url: str,
        token_request: SafeModeTokenRequest,
    ) -> str:
        log.debug("Requesting access token")

        response = self.session.http.post(
            token_url,
            json=asdict(token_request),
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "status": "OK",
                    "access_token": str,
                },
            ),
        )

        return response["access_token"]

    @staticmethod
    def _get_mdstrm_url(
        video_id: str,
        player_id: str,
        video_type: str,
        access_token: str | None = None,
    ) -> str:
        parsed_type = "live-stream" if video_type == "live" else "embed"

        params = {
            "player": player_id,
        }

        if access_token:
            params["access_token"] = access_token

        return f"https://mdstrm.com/{parsed_type}/{video_id}?{urlencode(params)}"

    # envivo
    def _get_envivo_streams(self, endpoint):
        stream_id = self.match["id"]

        config = self._get_envivo_config()
        log.debug(f"Player ID: {config.player_id}")

        if endpoint == self._MDSTRM_ENDPOINT_ENVIVO_LIVE:
            media = self._get_envivo_live_metadata(stream_id, config.client_id)
        elif endpoint == self._MDSTRM_ENDPOINT_ENVIVO_VOD:
            media = self._get_envivo_vod_metadata(stream_id, config.client_id)
        else:
            raise PluginError(f"Unsupported MDStrm endpoint: {endpoint}")

        if not media:
            return None

        playback = self._get_envivo_playback(
            endpoint=endpoint,
            media_id=media.id,
            player_id=config.player_id,
            app_version=config.app_version,
            access_token=media.access_token,
        )

        log.debug(f"Found HLS URL: {playback.hls_url}")

        params = {
            "dnt": "true",
            "player": config.player_id,
            "access_token": media.access_token,
            "uid": playback.uid,
            "sid": playback.sid,
            "pid": playback.pid,
            "an": self._ENVIVO_APP_NAME,
            "at": "web-app",
            "av": config.app_version,
            "sc": "0",
            "ref": self._ENVIVO_DOMAIN,
            "res": self._ENVIVO_DEFAULT_RESOLUTION,
            "ext_pb": "0",
            "CMCD": f'cid="{media.id}",mtp=500,ot=m,sf=h,sid="{playback.pid}",su',
        }

        streams = HLSStream.parse_variant_playlist(
            self.session,
            playback.hls_url,
            params=params,
            headers={
                "Referer": self._ENVIVO_REFERER,
            },
        )

        self.id = media.id
        self.title = media.title
        self.author = media.channel
        self.category = media.program

        return streams

    def _get_envivo_page_metadata(
        self,
        stream_id: str,
        client_id: str,
    ) -> EnVivoPageMedia | None:
        log.debug("Requesting page metadata")

        payload = [
            {
                "operationName": "getPlayerPageMedia",
                "variables": {
                    "id": stream_id,
                },
                "query": self._ENVIVO_PAGE_MEDIA_QUERY,
            },
        ]

        datatype, result = self._graphql(
            client_id,
            payload,
            {
                "data": {
                    "getMedia": validate.any(
                        None,
                        validate.all(
                            {
                                "_id": str,
                                "title": str,
                                "purchased": int,
                            },
                            validate.union_get(
                                "_id",
                                "title",
                                "purchased",
                            ),
                        ),
                    ),
                },
            },
            validate.get(("data", "getMedia")),
        )

        if datatype == "error":
            log.error(result)
            return None

        if result is None:
            log.error(f"No data found for media with ID {stream_id}")
            return None

        media_id, title, purchased = result

        return EnVivoPageMedia(
            id=media_id,
            title=title,
            purchased=purchased,
        )

    def _get_envivo_live_metadata(
        self,
        stream_id: str,
        client_id: str,
    ) -> EnVivoMedia | None:
        log.debug("Requesting live metadata")

        payload = [
            {
                "operationName": "getPlayerLive",
                "variables": {
                    "id": stream_id,
                },
                "query": self._ENVIVO_LIVE_QUERY,
            },
        ]

        datatype, result = self._graphql(
            client_id,
            payload,
            {
                "data": {
                    "getLive": validate.any(
                        None,
                        validate.all(
                            {
                                "_id": str,
                                "name": str,
                                "accessToken": validate.any(str, None),
                                "schedules": [
                                    validate.all(
                                        {
                                            "name": str,
                                            "current": bool,
                                        },
                                        validate.union_get(
                                            "name",
                                            "current",
                                        ),
                                    ),
                                ],
                            },
                            validate.union_get(
                                "_id",
                                "name",
                                "accessToken",
                                "schedules",
                            ),
                        ),
                    ),
                },
            },
            validate.get(("data", "getLive")),
        )

        if datatype == "error":
            log.error(result)
            return None

        if result is None:
            log.error("This video is not available. Content may be geo-blocked")
            return None

        media_id, channel, access_token, schedules = result

        if not access_token:
            raise PluginError("This video is not available for playback")

        program = next(
            (name for name, current in schedules if current),
            None,
        )

        return EnVivoMedia(
            id=media_id,
            title=channel,
            channel=channel,
            program=program,
            access_token=access_token,
        )

    def _get_envivo_vod_metadata(
        self,
        stream_id: str,
        client_id: str,
    ) -> EnVivoMedia | None:
        page = self._get_envivo_page_metadata(stream_id, client_id)
        if page is None:
            return None

        if page.purchased < 1:
            log.warning(
                f"Unexpected purchased value ({page.purchased}); attempting playback anyway",
            )

        log.debug("Requesting VOD metadata")

        payload = [
            {
                "operationName": "getPlayerMedia",
                "variables": {
                    "withDescription": False,
                    "id": page.id,
                },
                "query": self._ENVIVO_MEDIA_QUERY,
            },
        ]

        datatype, result = self._graphql(
            client_id,
            payload,
            {
                "data": {
                    "getMedia": validate.any(
                        None,
                        validate.all(
                            {
                                "_id": str,
                                "title": str,
                                "accessToken": validate.any(str, None),
                            },
                            validate.union_get(
                                "_id",
                                "title",
                                "accessToken",
                            ),
                        ),
                    ),
                },
            },
            validate.get(("data", "getMedia")),
        )

        if datatype == "error":
            log.error(result)
            return None

        if result is None:
            log.error("This video is not available. Content may be geo-blocked")
            return None

        media_id, title, access_token = result

        if access_token is None:
            raise PluginError("This video is not available for playback")

        return EnVivoMedia(
            id=media_id,
            title=title,
            access_token=access_token,
        )

    def _get_envivo_config(self) -> EnVivoConfig:
        app_url = self.session.http.get(
            f"https://next.platform.mediastre.am/ott?domain={self._ENVIVO_DOMAIN}",
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "status": "OK",
                    "data": validate.url(
                        hostname="next-apps.mdstrm.com",
                    ),
                },
                validate.get("data"),
            ),
        )

        client_id, player_id, app_version = self.session.http.get(
            url_concat(app_url, "release.json"),
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "config": {
                        "api": {
                            "headers": {
                                "x-client-id": str,
                            },
                        },
                        "app": {
                            "version": str,
                        },
                        "players": {
                            "playerVod": str,
                        },
                    },
                },
                validate.union_get(
                    ("config", "api", "headers", "x-client-id"),
                    ("config", "players", "playerVod"),
                    ("config", "app", "version"),
                ),
            ),
        )

        return EnVivoConfig(
            client_id=client_id,
            player_id=player_id,
            app_version=app_version,
        )

    def _get_envivo_playback(
        self,
        endpoint: str,
        media_id: str,
        player_id: str,
        app_version: str,
        access_token: str,
    ) -> EnVivoPlayback:
        hls_url, uid, sid, pid = self.session.http.get(
            f"https://mdstrm.com/{endpoint}/{media_id}.json",
            params={
                "validate": "true",
                "metadata": "true",
                "access_token": access_token,
                "player": player_id,
                "language": "es",
                "an": self._ENVIVO_APP_NAME,
                "at": "web-app",
                "av": app_version,
                "ref": self._ENVIVO_DOMAIN,
                "res": self._ENVIVO_DEFAULT_RESOLUTION,
            },
            headers={
                "Referer": self._ENVIVO_REFERER,
            },
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "src": {
                        "hls": validate.url(),
                    },
                    "MDSTRMUID": str,
                    "MDSTRMSID": str,
                    "MDSTRMPID": str,
                },
                validate.union_get(
                    ("src", "hls"),
                    "MDSTRMUID",
                    "MDSTRMSID",
                    "MDSTRMPID",
                ),
            ),
        )

        return EnVivoPlayback(
            hls_url=hls_url,
            uid=uid,
            sid=sid,
            pid=pid,
        )

    def _graphql(
        self,
        client_id: str,
        payload: list[dict],
        *schemas,
    ):
        return self.session.http.post(
            "https://next.mediastream.co/graphql",
            headers={
                "Referer": self._ENVIVO_REFERER,
                "Origin": self._ENVIVO_ORIGIN,
                "x-client-id": client_id,
                "x-ott-language": "es",
            },
            json=payload,
            schema=validate.Schema(
                validate.parse_json(),
                [
                    validate.any(
                        validate.all(
                            {
                                "errors": [
                                    {
                                        "message": str,
                                    },
                                ],
                            },
                            validate.get("errors"),
                            validate.length(1),
                            validate.transform(
                                lambda errors: (
                                    "error",
                                    ", ".join(error["message"] for error in errors),
                                ),
                            ),
                        ),
                        validate.all(
                            dict,
                            *schemas,
                            validate.transform(lambda data: ("success", data)),
                        ),
                    ),
                ],
                validate.get(0),
            ),
        )


__plugin__ = TVAzteca
