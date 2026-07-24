"""
$description Global live-streaming and video hosting social platform owned by Google.
$url youtube.com
$url youtu.be
$type live, vod
$webbrowser Used as a fallback when the Deno JavaScript runtime is not installed on the system
$metadata id
$metadata author
$metadata category
$metadata title
$notes Requires the yt_dlp_ejs package for access to higher quality streams and VODs.
$notes Requires the Deno JavaScript runtime, or uses Streamlink's webbrowser API as a fallback.
"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar
from urllib.parse import urlparse, urlunparse

import trio

from streamlink import PluginError, validate
from streamlink.compat import BaseExceptionGroup
from streamlink.logger import getLogger
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import useragents
from streamlink.stream.hls import HLSStream, MuxedHLSStream
from streamlink.utils.deno import DenoProcessor
from streamlink.utils.parse import parse_json, parse_qsd
from streamlink.utils.times import hours_minutes_seconds_float
from streamlink.webbrowser.cdp import CDPClient, devtools


if TYPE_CHECKING:
    from typing import Protocol

    from streamlink.session.session import Streamlink
    from streamlink.webbrowser.cdp import CDPClientSession

    class SolverModule(Protocol):
        def core(self) -> str: ...

        def lib(self) -> str: ...


yt_dlp_solver: SolverModule | None
try:
    from yt_dlp_ejs.yt import solver  # type: ignore # ty: ignore[unused-ignore-comment]

    yt_dlp_solver = solver  # type: ignore
except ImportError:
    yt_dlp_solver = None

log = getLogger(__name__)


@dataclass(frozen=True)
class NChallengeInput:
    player_url: str
    token: str


@dataclass(frozen=True)
class NChallengeOutput:
    solved: str | None = None


class Solver(ABC):
    def __init__(self, session: Streamlink):
        self._code_cache: dict[str, str] = {}  # player_url -> raw JS source text
        self.session = session

    @abstractmethod
    def _solve(self, js_input: str) -> dict | str | None:
        pass

    def solve(self, challenge: NChallengeInput) -> NChallengeOutput:
        player = self._get_player(challenge.player_url)
        if not player:
            log.error("Could not retrieve player JS for URL: %s", challenge.player_url)
            return NChallengeOutput()
        js_input = self._construct_input(player, challenge)

        output: dict | str | None = None
        try:
            output = self._solve(js_input)
        except BaseExceptionGroup:
            log.exception("n-challenge solving failed for token %r", challenge.token)
        except Exception as err:
            log.error(err)

        return self.validate_output(output, challenge)

    @staticmethod
    def validate_output(output: dict | str | None, request: NChallengeInput) -> NChallengeOutput:
        if output is None:
            return NChallengeOutput()

        def _filter_invalid_results(results: dict[str, str]) -> dict[str, str]:
            # When the JS solver throws internally it returns the input token as the
            # result, so a result that ends with the original challenge is a failure.
            return {k: v for k, v in results.items() if not v.endswith(k)}

        try:
            responses = validate.Schema(
                validate.any(
                    validate.all(str, validate.parse_json()),
                    dict,
                ),
                dict,
                lambda d: d.get("type", "") != "error",
            ).validate(output, name="solver output")

            result = validate.Schema(
                validate.get(("responses", 0)),
                dict,
                lambda d: d.get("type", "") != "error",
                validate.get("data"),
                {str: str},
                validate.transform(_filter_invalid_results),
                validate.get(request.token),
                validate.any(str, None),
                validate.transform(NChallengeOutput),
            ).validate(responses, name="challenge result")
            log.trace("Solver result: %r", result)
        except PluginError as e:
            log.error("Could not validate solver output: %s", e)
            result = NChallengeOutput()

        return result

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

    def _construct_input(self, player: str, request: NChallengeInput) -> str:
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
            log.trace("Fetching player JS: %s", player_url)
            code = self.session.http.get(player_url).text
            if code:
                self._code_cache[player_url] = code
                log.trace("Player JS cached (%d chars)", len(code))
            else:
                log.warning("Empty response for player JS URL: %s", player_url)
        return self._code_cache.get(player_url)


class DenoSolver(Solver):
    def __init__(self, session: Streamlink):
        super().__init__(session)
        self.deno = DenoProcessor()

    def _solve(self, js_input: str) -> str | None:
        self.deno.run(stdin=js_input.encode("utf-8"))
        return self.deno.output


class CDPSolver(Solver):
    def _solve(self, js_input: str) -> dict | None:
        sender, receiver = trio.open_memory_channel(1)

        async def on_main(client_session: CDPClientSession, request: devtools.fetch.RequestPaused):
            async with client_session.alter_request(request) as cm:
                cm.body = "<!doctype html>"

        async def collect_logs(client_session: CDPClientSession):
            async for event in client_session.cdp_session.listen(devtools.runtime.ConsoleAPICalled):
                for arg in event.args:
                    if arg.value is None:
                        continue
                    try:
                        # noinspection PyTypeChecker
                        res = json.loads(arg.value)
                    except (ValueError, TypeError, json.JSONDecodeError):
                        continue
                    if res.get("type"):
                        await sender.send(res)
                        return

        async def solve_n_challenge(client: CDPClient):
            async with client.session() as client_session:
                client_session.add_request_handler(on_main, url_pattern="https://*", on_request=True)
                async with client_session.navigate("https://www.youtube.com/") as frame_id:
                    await client_session.loaded(frame_id)
                    # Enable runtime to capture console events
                    await client_session.cdp_session.send(devtools.runtime.enable())
                    async with trio.open_nursery() as nursery:
                        nursery.start_soon(collect_logs, client_session)
                        await client_session.evaluate(js_input)
                        return await receiver.receive()

        return CDPClient.launch(self.session, solve_n_challenge)


class YoutubeAPI:
    SOLVERS: ClassVar[list[type[Solver]]] = [DenoSolver, CDPSolver]

    # Default client configurations
    # Each entry supplies default INNERTUBE_CONTEXT and the numeric client-name
    CLIENTS: dict = {
        "web_safari": {
            "INNERTUBE_CONTEXT": {
                "client": {
                    "clientName": "WEB",
                    "clientVersion": "2.20260114.08.00",
                    "userAgent": (
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
                        + "(KHTML, like Gecko) Version/15.5 Safari/605.1.15,gzip(gfe)"
                    ),
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
                    "userAgent": (
                        "com.google.android.apps.youtube.vr.oculus/1.65.10 (Linux; U; Android 12L; "
                        + "eureka-user Build/SQ3A.220605.009.A1) gzip"
                    ),
                    "osName": "Android",
                    "osVersion": "12L",
                },
            },
            "INNERTUBE_CONTEXT_CLIENT_NAME": 28,
        },
    }

    def __init__(self, session: Streamlink):
        self.session = session
        self.id: str | None = None
        self.author: str | None = None
        self.category: str | None = None
        self.title: str | None = None

    def _get_solver(self) -> Solver | None:
        for solverclass in self.SOLVERS:
            try:
                slvr = solverclass(session=self.session)
            except Exception as err:
                log.debug("Failed initializing n-challenge solver %s: %s", solverclass.__name__, err)
                continue
            else:
                log.debug("Initialized n-challenge solver %s", solverclass.__name__)
                return slvr

        log.warning("Could not initialize any n-challenge solvers")
        return None

    @staticmethod
    def get_data_from_regex(data: str, regex: re.Pattern, descr: str):
        if match := regex.search(data):
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

    @staticmethod
    def _schema_consent(data):
        schema_consent = validate.Schema(
            validate.parse_html(),
            validate.any(
                validate.xml_find(".//form[@action='https://consent.youtube.com/s']"),
                validate.all(
                    validate.xml_xpath(".//form[@action='https://consent.youtube.com/save']"),
                    validate.filter(lambda elem: elem.xpath(".//input[@type='hidden'][@name='set_ytc'][@value='true']")),
                    validate.get(0),
                ),
            ),
            validate.union((
                validate.get("action"),
                validate.xml_xpath(".//input[@type='hidden']"),
            )),
        )
        return schema_consent.validate(data)

    def _get_res(self, url: str, **kwargs):
        res = self.session.http.get(url, **kwargs)
        if urlparse(res.url).netloc == "consent.youtube.com":
            target, elems = self._schema_consent(res.text)
            c_data = {
                elem.attrib.get("name"): elem.attrib.get("value")
                for elem in elems
            }  # fmt: skip
            log.debug(f"consent target: {target}")
            log.debug(f"consent data: {', '.join(c_data.keys())}")
            res = self.session.http.post(target, data=c_data, **kwargs)
        return res

    def process_live_page(self, url: str) -> str:
        res = self._get_res(url)
        re_yt_initial_data = re.compile(r"""var\s+ytInitialData\s*=\s*({.*?})\s*;\s*</script>""", re.DOTALL)
        initial = self.get_data_from_regex(res.text, re_yt_initial_data, "initial data")
        video_id = self._schema_video_id(initial)
        if not video_id:
            raise ValueError("Unable to extract video ID from /live page")

        log.debug("Resolved video ID %s", video_id)
        return video_id

    def _get_webpage_data(self, url: str) -> dict:
        log.trace("Fetching watch page: %s", url)
        re_ytcfg = re.compile(r"ytcfg\.set\s*\(\s*({.+?})\s*\)\s*;")
        webpage = self._get_res(
            url,
            params={"bpctr": "9999999999", "has_verified": "1"},
            headers={"User-Agent": self.CLIENTS["web_safari"]["INNERTUBE_CONTEXT"]["client"]["userAgent"]},
        )
        self.extract_metadata(webpage.text)
        return self.get_data_from_regex(webpage.text, re_ytcfg, "ytcfg")

    @staticmethod
    def _build_headers(client_config: dict, visitor_data: str, client_context: dict) -> dict:
        default_client = client_config.get("INNERTUBE_CONTEXT", {}).get("client", {})
        client_version = client_context.get("clientVersion") or default_client.get("clientVersion")
        ua = client_context.get("userAgent") or default_client.get("userAgent")
        return {
            "X-YouTube-Client-Name": str(client_config.get("INNERTUBE_CONTEXT_CLIENT_NAME", "")),
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
                lambda url: f"https://www.youtube.com/{url.removeprefix('https://www.youtube.com').removeprefix('/')}",
            ),
        ).validate(data, name="_schema_player_url")

    def _extract_player_response(self, client: str, webpage_ytcfg: dict, visitor_data: str, video_id) -> dict:
        # Prefer live page context; fall back to static client config.
        client_config = self.CLIENTS[client].copy()
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

    def _extract_hls(self, player_responses: list[dict], player_url: str) -> str:
        slvr: Solver | None = None
        for response in player_responses:
            streaming_data = response.get("streamingData", {})

            hls_manifest_url = streaming_data.get("hlsManifestUrl", "")
            if not hls_manifest_url:
                log.trace("No hlsManifestUrl in streamingData: %r", streaming_data)
                continue

            # Solve the n-parameter challenge embedded in the manifest path.
            n_matches = re.findall(r"/n/([^/]+)/", urlparse(hls_manifest_url).path)
            if not n_matches:
                return hls_manifest_url
            n_token = n_matches[0]

            if yt_dlp_solver is None:
                log.debug("External JS for n-challenge solving not found. Skipping solving n-challenge %r", n_token)
                return hls_manifest_url

            log.trace("Attempting to solve n-challenge token: %s", n_token)
            if slvr is None:
                slvr = self._get_solver()
                if slvr is None:
                    return hls_manifest_url

            result = slvr.solve(NChallengeInput(token=n_token, player_url=player_url))
            if not result.solved:
                log.warning("Failed solving n-challenge token: %s", n_token)
                continue

            log.trace("n-challenge solved: %s -> %s", n_token, result.solved)
            return hls_manifest_url.replace(f"/n/{n_token}", f"/n/{result.solved}")

        return ""

    def process_watch_page(self, url: str, video_id: str) -> str:
        webpage_ytcfg = self._get_webpage_data(url)

        player_responses = []
        visitor_data = self._schema_visitor_data(webpage_ytcfg)
        player_url = self._schema_player_url(webpage_ytcfg)
        log.trace("Player JS URL: %s", player_url)
        for client in reversed(list(self.CLIENTS)):
            try:
                response = self._extract_player_response(client, webpage_ytcfg, visitor_data, video_id)
            except Exception as exc:
                log.error("Player request failed for client %s: %s", client, exc)
                continue

            player_responses.append(response)

        if not player_responses:
            log.warning("Failed to extract any player response with streamingData")
            return ""

        if not (hls := self._extract_hls(player_responses, player_url)):
            return ""

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

    def _get_data_from_api(self, url, video_id):
        res = self._get_res(url)
        re_innertube_api_key = re.compile(
            r"""(?P<q1>["'])INNERTUBE_API_KEY(?P=q1)\s*:\s*(?P<q2>["'])(?P<data>.+?)(?P=q2)""",
            re.DOTALL,
        )
        if m := re.search(re_innertube_api_key, res.text):
            api_key = m.group("data")
        else:
            api_key = "AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8"
            log.trace("Could not find API key in the page data. Applying a default key: %r", api_key)

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

    def get_streams_from_api(self, url: str, video_id: str) -> str | None:
        self.extract_metadata(url=url)
        if not (data := self._get_data_from_api(url, video_id)):
            return None
        status, reason = self._schema_playability_status(data)

        # assume that there's an error if reason is set (status will still be "OK" for some reason)
        if status != "OK" or reason:
            log.error("Could not get video info - %s: %s", status, reason)
            return None

        if not (hls_url := self._schema_streamingdata(data)):
            return None

        return hls_url

    @classmethod
    def _schema_videodetails(cls, data):
        schema = validate.Schema(
            {
                "videoDetails": {
                    "videoId": str,
                    "author": str,
                    "title": str,
                },
                "microformat": validate.all(
                    validate.any(
                        validate.all(
                            {"playerMicroformatRenderer": dict},
                            validate.get("playerMicroformatRenderer"),
                        ),
                        validate.all(
                            {"microformatDataRenderer": dict},
                            validate.get("microformatDataRenderer"),
                        ),
                    ),
                    {
                        "category": str,
                    },
                ),
            },
            validate.union_get(
                ("videoDetails", "videoId"),
                ("videoDetails", "author"),
                ("microformat", "category"),
                ("videoDetails", "title"),
            ),
        )
        return schema.validate(data)

    def extract_metadata(self, data: str | None = None, url: str | None = None):
        if not data and url is not None:
            data = self._get_res(url).text
        if not data:
            return

        re_yt_initial_player_response = re.compile(
            r"var\s+ytInitialPlayerResponse\s*=\s*({.*?});\s*(?:var\s+\w+\s*=|</script>)",
            re.DOTALL,
        )
        init_player_response = self.get_data_from_regex(data, re_yt_initial_player_response, "initial player response")
        self.id, self.author, self.category, self.title = self._schema_videodetails(init_player_response)


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
    _url_canonical: str = "https://www.youtube.com/watch?v={video_id}"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api = YoutubeAPI(self.session)

        if self.matches["channel"] and not self.match["live"]:
            self.url = f"{self.url.removesuffix('/')}/live"

        parsed = urlparse(self.url)
        params = parse_qsd(parsed.query)

        try:
            self.time_offset = hours_minutes_seconds_float(params.get("t", "0"))
        except ValueError:
            self.time_offset = 0

        if self.matches["default"] or self.matches["shorthand"]:
            self.url = self._url_canonical.format(video_id=self.match["video_id"])
        else:
            self.url = urlunparse(parsed._replace(scheme="https", netloc="www.youtube.com"))

        self.session.http.headers.update({"User-Agent": useragents.CHROME})

    def _get_streams(self) -> dict[str, HLSStream | MuxedHLSStream[HLSStream]] | None:
        if self.matches["channel"] and self.match["channel"]:
            video_id = self.api.process_live_page(self.url)
            self.url = self._url_canonical.format(video_id=video_id)

        params: dict = dict(start_offset=self.time_offset)
        try:
            hls_url: str | None = self.api.process_watch_page(self.url, self.match["video_id"])
            if not hls_url:
                raise ValueError(f"No HLS URLs found for videoId={self.match['video_id']}")

        except (PluginError, ValueError) as err:
            log.error("Failed finding data, falling back to YouTube API: %s", err)
            hls_url = self.api.get_streams_from_api(self.url, self.match["video_id"])
            if not hls_url:
                return None
            params.update(name_key="pixels")

        finally:
            self.id, self.author, self.category, self.title = self.api.id, self.api.author, self.api.category, self.api.title

        return HLSStream.parse_variant_playlist(self.session, hls_url, **params)


__plugin__ = YouTube
