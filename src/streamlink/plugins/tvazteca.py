"""
$description Live TV channels and video on-demand service from TV Azteca, a Mexican free-to-air broadcaster.
$url tvazteca.com
$url adn40.mx
$type live, vod
$region Mexico
"""

import json
import re
from dataclasses import asdict, dataclass
from urllib.parse import urlencode, urlparse

from streamlink import PluginError
from streamlink.logger import getLogger
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.plugins.mdstrm import MDStrm
from streamlink.stream.hls import HLSStream


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
        r"https?://(?:www\.)?tvazteca\.com/(?P<path>.+?)/?$",
    ),
)
@pluginmatcher(
    name="adn40",
    pattern=re.compile(
        r"https?://(?:www|live)\.adn40\.mx(?:/(?P<path>.*))?$",
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

        mdstrm = MDStrm(self.session, page.embed_url)
        streams = mdstrm._get_streams()

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

        player = root.find(".//div[@data-video-player][@data-video-id][@data-player-id]")

        if player is not None:
            video_id = player.attrib["data-video-id"]
            player_id = player.attrib["data-player-id"]
            video_type = player.attrib["data-video-type"]

            access_token = None

            if safe_mode := player.attrib.get("data-safe-mode-config"):
                safe_mode = json.loads(safe_mode)
                body = json.loads(safe_mode["bodyJson"])

                access_token = self._request_access_token(
                    safe_mode["domain"],
                    SafeModeTokenRequest(
                        asset_id=body["asset_id"],
                        type=body["type"],
                        token=body["token"],
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
                title=player.attrib.get("data-video-title") or None,
                channel=player.attrib.get("data-video-channel") or None,
                program=player.attrib.get("data-video-program") or None,
            )

        for script in root.xpath(".//script[@type='application/ld+json']"):
            try:
                data = json.loads(script.text)
            except (TypeError, ValueError):
                continue

            if isinstance(data, dict):
                data = [data]

            for item in data:
                if item.get("@type") != "VideoObject":
                    continue

                embed_url = item.get("embedUrl")
                if not isinstance(embed_url, str):
                    continue

                path = urlparse(embed_url).path.rstrip("/")
                if not path:
                    raise PluginError(f"Invalid MDStrm embed URL: {embed_url}")
                video_id = path.rsplit("/", 1)[-1]

                return TVAztecaPage(
                    video_id=video_id,
                    embed_url=embed_url,
                    title=item.get("name") or None,
                    channel=item.get("mainEntityOfPage", {}).get("publisher", {}).get("name", {}) or None,
                )

        raise PluginError("Unable to locate supported video metadata")

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

        media = self._get_envivo_media_metadata(endpoint, stream_id, config.client_id)

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
    ) -> EnVivoPageMedia:
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

        response = self._graphql(client_id, payload)

        result = validate.Schema(
            {
                "data": {
                    "getMedia": {
                        "_id": str,
                        "title": str,
                        "purchased": int,
                    },
                },
            },
        ).validate(response[0])["data"]["getMedia"]

        return EnVivoPageMedia(
            id=result["_id"],
            title=result["title"],
            purchased=result["purchased"],
        )

    def _get_envivo_media_metadata(
        self,
        endpoint: str,
        stream_id: str,
        client_id: str,
    ) -> EnVivoMedia:
        is_live = endpoint == self._MDSTRM_ENDPOINT_ENVIVO_LIVE
        is_vod = endpoint == self._MDSTRM_ENDPOINT_ENVIVO_VOD

        id_key = "_id"

        if is_live:
            log.debug("Requesting live metadata")

            payload = [
                {
                    "operationName": "getPlayerLive",
                    "variables": {"id": stream_id},
                    "query": self._ENVIVO_LIVE_QUERY,
                },
            ]
            field = "getLive"
            title_key = "name"
            schema = {
                id_key: str,
                title_key: str,
                "accessToken": validate.any(str, None),
                "schedules": [
                    {
                        "name": str,
                        "current": bool,
                    },
                ],
            }
        elif is_vod:
            page = self._get_envivo_page_metadata(stream_id, client_id)

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
            field = "getMedia"
            title_key = "title"
            schema = {
                id_key: str,
                title_key: str,
                "accessToken": validate.any(str, None),
            }
        else:
            raise PluginError(f"Unsupported MDStrm endpoint: {endpoint}")

        response = self._graphql(client_id, payload)
        if response:
            result = validate.Schema(
                {
                    "data": {
                        field: schema,
                    },
                },
            ).validate(response[0])["data"][field]
        else:
            raise PluginError(f"No data found for media with ID {stream_id}")

        access_token = result["accessToken"]
        if not access_token:
            raise PluginError("This video is not available for playback")

        channel = None
        program = None
        if is_live:
            channel = result[title_key]
            program = next(
                (schedule["name"] for schedule in result["schedules"] if schedule["current"]),
                None,
            )

        return EnVivoMedia(
            id=result[id_key],
            title=result[title_key],
            channel=channel,
            program=program,
            access_token=access_token,
        )

    def _get_envivo_config(self) -> EnVivoConfig:
        app = self.session.http.get(
            f"https://next.platform.mediastre.am/ott?domain={self._ENVIVO_DOMAIN}",
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "status": "OK",
                    "data": validate.url(),
                },
            ),
        )

        response = self.session.http.get(
            f"{app['data']}/release.json",
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
            ),
        )

        config = response["config"]

        return EnVivoConfig(
            client_id=config["api"]["headers"]["x-client-id"],
            player_id=config["players"]["playerVod"],
            app_version=config["app"]["version"],
        )

    def _get_envivo_playback(
        self,
        endpoint: str,
        media_id: str,
        player_id: str,
        app_version: str,
        access_token: str,
    ) -> EnVivoPlayback:
        response = self.session.http.get(
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
                    "title": str,
                    "MDSTRMUID": str,
                    "MDSTRMSID": str,
                    "MDSTRMPID": str,
                },
            ),
        )

        return EnVivoPlayback(
            hls_url=response["src"]["hls"],
            uid=response["MDSTRMUID"],
            sid=response["MDSTRMSID"],
            pid=response["MDSTRMPID"],
        )

    def _graphql(self, client_id: str, payload: list[dict]) -> list[dict]:
        response = self.session.http.post(
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
                list,
            ),
        )

        if not response:
            raise PluginError("Empty GraphQL response")

        for result in response:
            if "errors" in result:
                messages = ", ".join(error.get("message", "Unknown error") for error in result["errors"])
                raise PluginError(messages)

        return response


__plugin__ = TVAzteca
