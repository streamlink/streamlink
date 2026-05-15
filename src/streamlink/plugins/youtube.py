"""
$description Global live-streaming and video hosting social platform owned by Google.
$url youtube.com
$url youtu.be
$type live
$metadata id
$metadata author
$metadata category
$metadata title
$notes VOD content and protected videos are not supported
"""
from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from urllib.parse import urlparse, urlunparse

import trio

from streamlink import PluginError, validate
from streamlink.compat import BaseExceptionGroup
from streamlink.logger import getLogger
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import useragents
from streamlink.stream.hls import HLSStream
from streamlink.utils.deno import DenoProcessor
from streamlink.utils.parse import parse_json, parse_qsd
from streamlink.utils.times import hours_minutes_seconds_float
from streamlink.webbrowser.cdp import CDPClient, devtools


if TYPE_CHECKING:
    from typing import Protocol

    from requests import Response

    from streamlink.session.session import Streamlink
    from streamlink.webbrowser.cdp import CDPClientSession

    class SolverModule(Protocol):
        def core(self) -> str: ...

        def lib(self) -> str: ...

yt_dlp_solver: SolverModule | None
try:
    from yt_dlp_ejs.yt import solver  # type: ignore[import-not-found,import-untyped]

    yt_dlp_solver = solver  # type: ignore[ty:invalid-assignment]
except ImportError:
    yt_dlp_solver = None

log = getLogger(__name__)

# Default client configurations
# Each entry supplies default INNERTUBE_CONTEXT and the numeric client-name
CLIENTS: dict = {
    "web_safari": {
        "INNERTUBE_CONTEXT": {
            "client": {
                "clientName": "WEB",
                "clientVersion": "2.20260114.08.00",
                "userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
                             + "(KHTML, like Gecko) Version/15.5 Safari/605.1.15,gzip(gfe)",
            },
        },
        "INNERTUBE_CONTEXT_CLIENT_NAME": 1,
    },
    "android_vr": {
        "INNERTUBE_CONTEXT": {
            "client": {
                "clientName": "ANDROID_VR",
                "clientVersion": "1.65.10",
                "deviceMake": "Oculus",
                "deviceModel": "Quest 3",
                "androidSdkVersion": 32,
                "userAgent": "com.google.android.apps.youtube.vr.oculus/1.65.10 (Linux; U; Android 12L; "
                             + "eureka-user Build/SQ3A.220605.009.A1) gzip",
                "osName": "Android",
                "osVersion": "12L",
            },
        },
        "INNERTUBE_CONTEXT_CLIENT_NAME": 28,
    },
}

_re_ytInitialData = re.compile(r"""var\s+ytInitialData\s*=\s*({.*?})\s*;\s*</script>""", re.DOTALL)
_re_ytInitialPlayerResponse = re.compile(r"""var\s+ytInitialPlayerResponse\s*=\s*({.*?});\s*</script>""", re.DOTALL)
_re_innertube_api_key = re.compile(r"""(?P<q1>["'])INNERTUBE_API_KEY(?P=q1)\s*:\s*(?P<q2>["'])(?P<data>.+?)(?P=q2)""",
                                   re.DOTALL)
_re_ytcfg = re.compile(r"ytcfg\.set\s*\(\s*({.+?})\s*\)\s*;")

_url_canonical: str = "https://www.youtube.com/watch?v={video_id}"


@dataclass(frozen=True)
class NChallengeInput:
    player_url: str
    token: str


@dataclass(frozen=True)
class NChallengeOutput:
    results: dict[str, str] = field(default_factory=dict)


class Solver(ABC):
    def __init__(self, session: Streamlink):
        super().__init__()
        self._code_cache: dict[str, str] = {}  # player_url -> raw JS source text
        self.session = session

    @abstractmethod
    def solve(self, challenge: NChallengeInput) -> NChallengeOutput | None:
        pass

    @staticmethod
    def validate_output(output: str | dict, request: NChallengeInput) -> NChallengeOutput:
        if isinstance(output, str):
            output = json.loads(output)
        elif output.get("type") == "error":
            raise ValueError(f"Solver top-level error: {output['error']}")

        if not isinstance(output, dict):
            raise ValueError(f"Invalid solver output type: {type(output)!r} but 'dict' expected")

        response_data = output["responses"][0]
        if response_data.get("type") == "error":
            raise ValueError(f"Solver response error for challenge {request.token!r}: {response_data['error']}")

        response = NChallengeOutput(response_data["data"])
        log.debug("Raw solver response: %s", response)

        if not isinstance(response, NChallengeOutput):
            log.warning("Response is not an NChallengeOutput")

        if not (
            all(isinstance(k, str) and isinstance(v, str) for k, v in response.results.items())
            and request.token in response.results
        ):
            log.warning("Invalid NChallengeOutput: missing token or non-string entries")

        # When the JS solver throws internally it returns the input token as the
        # result, so a result that ends with the original challenge is a failure.
        for challenge, result in response.results.items():
            if result.endswith(challenge):
                log.warning("n result is invalid for %r: %r", challenge, result)

        return response

    @staticmethod
    def _get_script(script_type: str) -> str:
        if yt_dlp_solver is None:
            raise ValueError("yt_dlp_ejs package is not installed")
        try:
            return yt_dlp_solver.core() if script_type == "core" else yt_dlp_solver.lib()
        except Exception as exc:
            raise ValueError(
                f'Failed to load solver "{script_type}" script from package: {exc}',
            ) from exc

    def _construct_stdin(self, player: str, request: NChallengeInput) -> str:
        data = {
            "type": "player",
            "player": player,
            "requests": [{"type": "n", "challenges": [request.token]}],
            "output_preprocessed": True,
        }
        return (
            f"{self._get_script('lib')}\n"
            + "Object.assign(globalThis, lib);\n"
            + f"{self._get_script('core')}\n"
            + f"console.log(JSON.stringify(jsc({json.dumps(data)})));\n"
        )

    def _get_player(self, player_url: str) -> str | None:
        if player_url not in self._code_cache:
            log.debug("Fetching player JS: %s", player_url)
            code = self.session.http.get(player_url).text
            if code:
                self._code_cache[player_url] = code
                log.debug("Player JS cached (%d chars)", len(code))
            else:
                log.warning("Empty response for player JS URL: %s", player_url)
        return self._code_cache.get(player_url)


class DenoSolver(Solver):
    def solve(self, challenge: NChallengeInput) -> NChallengeOutput | None:
        log.debug("Solving n-challenge token %r via Deno", challenge.token)
        try:
            player = self._get_player(challenge.player_url)
            if not player:
                log.error("Could not retrieve player JS for URL: %s", challenge.player_url)
                return None

            stdin = self._construct_stdin(player, challenge)
            deno = DenoProcessor(stdin=stdin)
            deno.run()
            stdout = deno.output
            return self.validate_output(stdout, challenge)

        except Exception as exc:
            log.error("n-challenge solving failed for token %r: %s", challenge.token, exc)
            if "The system cannot find the file specified" in str(exc):
                raise PluginError("Deno not found. Please install Deno from "
                                  + "https://deno.land/manual/getting_started/installation") from exc
            return NChallengeOutput(results={})


class CDPSolver(Solver):

    def solve(self, challenge: NChallengeInput) -> NChallengeOutput | None:
        events: list[devtools.runtime.ConsoleAPICalled] | None = None
        eval_timeout = self.session.get_option("webbrowser-timeout")
        url = challenge.player_url

        player = self._get_player(challenge.player_url)
        if not player:
            log.error("Could not retrieve player JS for URL: %s", challenge.player_url)
            return None
        stdin = self._construct_stdin(player, challenge)

        async def on_main(client_session: CDPClientSession, request: devtools.fetch.RequestPaused):
            async with client_session.alter_request(request) as cm:
                cm.body = "<!doctype html>"

        async def solve_n_challenge(client: CDPClient):
            async with client.session() as client_session:
                client_session.add_request_handler(on_main, url_pattern=url, on_request=True)

                async with client_session.navigate(url) as frame_id:
                    await client_session.loaded(frame_id)
                    logs = []

                    # Enable runtime to capture console events
                    await client_session.cdp_session.send(devtools.runtime.enable())

                    async def collect_logs():
                        async for event in client_session.cdp_session.listen(devtools.runtime.ConsoleAPICalled):
                            logs.append(event)

                    async with trio.open_nursery() as nursery:
                        nursery.start_soon(collect_logs)
                        await client_session.evaluate(stdin, timeout=eval_timeout)
                        nursery.cancel_scope.cancel()

                    return logs

        try:
            events = CDPClient.launch(self.session, solve_n_challenge)
        except BaseExceptionGroup:
            log.exception("Failed acquiring client integrity token")
        except Exception as err:
            log.error(err)

        if not events:
            return None

        stdout = {}
        for event in events:
            for arg in event.args:
                try:
                    if arg.value is None:
                        continue
                    stdout = json.loads(arg.value)
                    if stdout.get("type"):
                        break
                except Exception:
                    pass

        return self.validate_output(stdout, challenge)


class YoutubeAPI:

    def __init__(self, session: Streamlink):
        self.session = session

    @staticmethod
    def get_data_from_regex(res: Response, regex, descr: str):
        if match := re.search(regex, res.text):
            return parse_json(match.group(1))
        raise PluginError(f"Pattern not found in response body: {descr}")

    @staticmethod
    def _schema_video_id(data) -> str | None:
        return validate.Schema(
            {
                "currentVideoEndpoint": {
                    "watchEndpoint": {"videoId": str},
                },
            },
            validate.get(("currentVideoEndpoint", "watchEndpoint", "videoId")),
        ).validate(data, name="_schema_video_id")

    def process_live_page(self, url: str) -> str:
        res = self.session.http.get(url)
        initial = self.get_data_from_regex(res, _re_ytInitialData, "initial data")
        video_id = self._schema_video_id(initial)
        if not video_id:
            raise ValueError("Unable to extract video ID from /live page")

        log.debug("Resolved video ID %s", video_id)
        return video_id

    def _get_webpage_data(self, url: str) -> dict:
        log.debug("Fetching watch page: %s", url)
        headers = {
            **self.session.http.headers,
            "User-Agent": CLIENTS["web_safari"]["INNERTUBE_CONTEXT"]["client"]["userAgent"],
        }
        webpage = self.session.http.get(url, params={"bpctr": "9999999999", "has_verified": "1"}, headers=headers)
        return self.get_data_from_regex(webpage, _re_ytcfg, "ytcfg")

    @staticmethod
    def _build_headers(client_config: dict, visitor_data: str, client_context: dict) -> dict:
        default_client = client_config.get("INNERTUBE_CONTEXT", {}).get("client", {})
        client_version = client_context.get("clientVersion") or default_client.get("clientVersion")
        ua = client_context.get("userAgent") or default_client.get("userAgent")
        return {
            "X-YouTube-Client-Name": str(client_config.get("INNERTUBE_CONTEXT_CLIENT_NAME")),
            "X-YouTube-Client-Version": client_version,
            "Origin": "https://www.youtube.com",
            "X-Goog-Visitor-Id": visitor_data,
            "User-Agent": ua,
            "content-type": "application/json",
        }

    @staticmethod
    def _build_player_request_payload(client_context: dict, webpage_ytcfg: dict, video_id) -> dict:
        return {
            "context": client_context,
            "videoId": video_id,
            "playbackContext": {
                "contentPlaybackContext": {
                    "html5Preference": "HTML5_PREF_WANTS",
                    **({"signatureTimestamp": sts} if (sts := webpage_ytcfg.get("STS")) else {}),
                },
            },
            "contentCheckOk": True,
            "racyCheckOk": True,
        }

    @staticmethod
    def _schema_visitor_data(data) -> str:
        return validate.Schema(
            validate.any(
                validate.all({"VISITOR_DATA": str}, validate.get("VISITOR_DATA")),
                validate.all(
                    {"INNERTUBE_CONTEXT": {"client": {"visitorData": str}}},
                    validate.get(("INNERTUBE_CONTEXT", "client", "visitorData")),
                ),
            ),
        ).validate(data, name="_schema_visitor_data")

    @staticmethod
    def _schema_player_url(data) -> str:
        return validate.Schema(
            validate.any(
                validate.all({"PLAYER_JS_URL": str}, validate.get("PLAYER_JS_URL")),
                validate.all(
                    {"WEB_PLAYER_CONTEXT_CONFIGS": {str: {"jsUrl": str}}},
                    validate.get("WEB_PLAYER_CONTEXT_CONFIGS"),
                    validate.transform(lambda x: next(iter(x.values()))),
                    validate.get("jsUrl"),
                ),
            ),
            validate.transform(
                lambda url: url if url.startswith("https://www.youtube.com")
                else f"https://www.youtube.com/{url.removeprefix('https://www.youtube.com').removeprefix('/')}",
            ),
        ).validate(data, name="_schema_player_url")

    def _extract_player_response(self, client: str, webpage_ytcfg: dict, visitor_data: str, video_id) -> dict:
        # Prefer live page context; fall back to static client config.
        client_config = CLIENTS[client].copy()
        context = webpage_ytcfg.get("INNERTUBE_CONTEXT") or client_config.get("INNERTUBE_CONTEXT", {})
        client_context = context.get("client", {})
        client_context.update({"hl": "en", "timeZone": "UTC", "utcOffsetMinutes": 0})

        headers = self._build_headers(client_config, visitor_data, client_context)
        payload = self._build_player_request_payload(context, webpage_ytcfg, video_id)
        return self.session.http.post(
            "https://www.youtube.com/youtubei/v1/player",
            params={"prettyPrint": "false"},
            headers=headers,
            json=payload,
            schema=validate.Schema(
                validate.parse_json(),
                {"streamingData": dict},
            ),
        )

    def _extract_hls(self, player_responses: list[dict], player_url: str) -> list[str]:
        hls_list = []
        slvr: Solver
        try:
            DenoProcessor.resolve_path()
            slvr = DenoSolver(self.session)
        except FileNotFoundError as e:
            log.warning(str(e))
            slvr = CDPSolver(self.session)

        for response in player_responses:
            streaming_data = response.get("streamingData", {})

            hls_manifest_url = streaming_data.get("hlsManifestUrl")
            if not hls_manifest_url:
                log.debug("No hlsManifestUrl in streamingData: %s", streaming_data)
                continue

            # Solve the n-parameter challenge embedded in the manifest path.
            n_matches = re.findall(r"/n/([^/]+)/", urlparse(hls_manifest_url).path)
            if n_matches and yt_dlp_solver is None:
                log.warning("yt_dlp_ejs package not installed. Skipping solving n-challenge %r", n_matches[0])

            elif n_matches:
                n_token = n_matches[0]
                log.debug("Solving n-challenge token: %s", n_token)
                result = slvr.solve(NChallengeInput(token=n_token, player_url=player_url))

                if result and (solved := result.results.get(n_token)):
                    hls_manifest_url = hls_manifest_url.replace(f"/n/{n_token}", f"/n/{solved}")
                    log.debug("n-challenge solved: %s -> %s", n_token, solved)
                    hls_list.append(hls_manifest_url)
                else:
                    log.warning("Failed to solve n-challenge token: %s", n_token)
            else:
                hls_list.append(hls_manifest_url)

        log.debug("Collected %d HLS manifest URL(s)", len(hls_list))
        return hls_list

    def process_watch_page(self, url: str, video_id: str) -> list[str]:
        webpage_ytcfg = self._get_webpage_data(url)

        player_responses = []
        visitor_data = self._schema_visitor_data(webpage_ytcfg)
        player_url = self._schema_player_url(webpage_ytcfg)
        log.debug("Player JS URL: %s", player_url)
        for client in reversed(list(CLIENTS)):
            try:
                response = self._extract_player_response(client, webpage_ytcfg, visitor_data, video_id)
            except Exception as exc:
                log.error("Player request failed for client %s: %s", client, exc)
                continue

            player_responses.append(response)

        if not player_responses:
            log.warning("Failed to extract any player response with streamingData")
            return []

        hls = self._extract_hls(player_responses, player_url)
        if not hls:
            raise ValueError(f"No HLS URLs found for a videoId={video_id}")

        log.debug("HLS extraction succeeded. Extracted %d URLs", len(hls))
        return hls

    @classmethod
    def _schema_playability_status(cls, data):
        schema = validate.Schema(
            {
                "playabilityStatus": {
                    "status": str,
                    validate.optional("reason"): validate.any(str, None),
                },
            },
            validate.get("playabilityStatus"),
            validate.union_get("status", "reason"),
        )
        return schema.validate(data, name="_schema_playability_status")

    @classmethod
    def _schema_streamingdata(cls, data):
        return validate.Schema(
            {
                "streamingData": {
                    validate.optional("hlsManifestUrl"): str,
                },
            },
            validate.get("streamingData"),
            validate.get("hlsManifestUrl"),
        ).validate(data, name="_schema_streamingdata")

    def _get_data_from_api(self, res, video_id):
        if m := re.search(_re_innertube_api_key, res.text):
            api_key = m.group("data")
        else:
            api_key = "AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8"
            log.debug("Could not find API key in the page data. Applying a default key: %r", api_key)

        return self.session.http.post(
            "https://www.youtube.com/youtubei/v1/player",
            headers={"Content-Type": "application/json"},
            params={"key": api_key},
            json={
                "videoId": video_id,
                "contentCheckOk": True,
                "racyCheckOk": True,
                "context": {
                    "client": {
                        "clientName": "ANDROID",
                        "clientVersion": "21.08.266",
                        "platform": "DESKTOP",
                        "clientScreen": "EMBED",
                        "clientFormFactor": "UNKNOWN_FORM_FACTOR",
                        "browserName": "Chrome",
                    },
                    "user": {"lockedSafetyMode": "false"},
                    "request": {"useSsl": "true"},
                },
            },
            schema=validate.Schema(
                validate.parse_json(),
            ),
        )

    def get_streams_from_api(self, url, video_id) -> dict:
        res = self.session.http.get(url)

        if not (data := self._get_data_from_api(res, video_id)):
            return {}
        status, reason = self._schema_playability_status(data)

        # assume that there's an error if reason is set (status will still be "OK" for some reason)
        if status != "OK" or reason:
            log.error("Could not get video info - %s: %s", status, reason)
            return {}

        streams = {}
        hls_manifest = self._schema_streamingdata(data)

        if hls_manifest:
            streams.update(HLSStream.parse_variant_playlist(self.session, hls_manifest, name_key="pixels"))

        if not streams:
            raise ValueError("Cound not find a HLS manifest. "
                             + "This plugin does not support VOD content, try yt-dlp instead if necessary")

        return streams


@pluginmatcher(
    name="default",
    pattern=re.compile(
        r"https?://(?:\w+\.)?youtube\.com/(?:v/|live/|embed/|watch\?(?:\S*&)?v=)(?P<video_id>[\w-]{11})",
    ),
)
@pluginmatcher(
    name="channel",
    pattern=re.compile(
        r"https?://(?:\w+\.)?youtube\.com/(?:@|c(?:hannel)?/|user/)?(?P<channel>[^/?]+)(?P<live>/live)?/?$",
    ),
)
@pluginmatcher(
    name="shorthand",
    pattern=re.compile(
        r"https?://youtu\.be/(?P<video_id>[\w-]{11})",
    ),
)
class YouTube(Plugin):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        parsed = urlparse(self.url)
        params = parse_qsd(parsed.query)

        try:
            self.time_offset = hours_minutes_seconds_float(params.get("t", "0"))
        except ValueError:
            self.time_offset = 0

        if self.matches["default"] or self.matches["shorthand"]:
            self.url = _url_canonical.format(video_id=self.match["video_id"])
        else:
            self.url = urlunparse(parsed._replace(scheme="https", netloc="www.youtube.com"))

        self.session.http.headers.update({"User-Agent": useragents.CHROME})

    def _get_streams(self):
        api = YoutubeAPI(self.session)

        if self.matches["channel"] and self.match["channel"]:
            video_id = api.process_live_page(self.url)
            self.url = _url_canonical.format(video_id=video_id)

        try:
            m3u8_urls = api.process_watch_page(self.url, self.match["video_id"])
            return HLSStream.parse_variant_playlist(self.session, m3u8_urls[0]).items()

        except (PluginError, ValueError) as e:
            log.error("Extraction failed: %s", e)
            log.info("Falling back to YouTube API")
            return api.get_streams_from_api(self.url, self.match["video_id"]).items()


__plugin__ = YouTube
