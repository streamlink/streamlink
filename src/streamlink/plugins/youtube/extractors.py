"""YouTube data extractors for video and channel/live pages.

Provides extractors that handle:
- Tab pages (channel/live pages) -> video URLs
- Video pages -> HLS manifest URLs with n-challenge solving
"""

import json
import logging
import re
import time
from urllib.parse import urlparse, urlunparse

from requests import Response

from streamlink.plugin.api import validate
from streamlink.utils.parse import parse_json

from .structures import NChallengeInput, ExtractorType, ExtractorResult, NextExtractor, StreamSelection, ctx, StreamPick

log = logging.getLogger(__name__)

# Default client configurations
# Each entry supplies default INNERTUBE_CONTEXT and the numeric client-name
CLIENTS = {
    "web_safari": {
        "INNERTUBE_CONTEXT": {
            "client": {
                "clientName": "WEB",
                "clientVersion": "2.20260114.08.00",
                "userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
                             "(KHTML, like Gecko) Version/15.5 Safari/605.1.15,gzip(gfe)",
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
                             "eureka-user Build/SQ3A.220605.009.A1) gzip",
                "osName": "Android",
                "osVersion": "12L",
            },
        },
        "INNERTUBE_CONTEXT_CLIENT_NAME": 28,
    },
}

_re_ytInitialData = re.compile(
    r"""var\s+ytInitialData\s*=\s*({.*?})\s*;\s*</script>""",
    re.DOTALL,
)


def _get_data_from_regex(res: Response, regex, descr: str):
    """Search *res.text* with *regex* and parse the first capture group as JSON.

    Args:
        res:   HTTP response whose text body is searched.
        regex: Compiled or string pattern with one capture group.
        descr: Human-readable label used in the debug log when no match is found.

    Returns:
        Parsed JSON object, or ``None`` if the pattern did not match.
    """
    if match := re.search(regex, res.text):
        return parse_json(match.group(1))
    log.debug("Pattern not found in response body: %s", descr)


class StreamsExtractor:
    """Resolves a YouTube ``/streams`` page to a watch URL.

    Fetches the channel streams page, extracts ``ytInitialData``, filters
    active (non-upcoming) streams, and redirects to the selected video.
    """

    valid_url_re = r"https://www\.youtube\.com/(?:@|c(?:hannel)?/|user/)?(?P<id>[^/?\\#&]+)/streams"
    extractor_type: ExtractorType = ExtractorType.LIVE

    @staticmethod
    def _get_initial_data(url) -> dict:
        """Fetch and return ``ytInitialData`` from *url*, retrying up to 3 times.

        Args:
            url: Channel streams page URL.

        Returns:
            Parsed ``ytInitialData`` dict, or ``{}`` if all attempts fail.
        """
        for attempt in range(1, 4):
            try:
                log.debug("Fetching ytInitialData (attempt %d): %s", attempt, url)
                webpage = ctx.session.http.get(url)
                return _get_data_from_regex(webpage, _re_ytInitialData, "ytInitialData")
            except Exception as exc:
                log.error("Error fetching ytInitialData (attempt %d): %s", attempt, exc)
        log.warning("All attempts to fetch ytInitialData failed for: %s", url)
        return {}

    @staticmethod
    def _schema_tab_data(data) -> dict | None:
        """Extract the contents list from the currently selected tab.

        Navigates ``ytInitialData`` to find the active ``richGridRenderer``
        tab and returns its ``contents`` list.

        Args:
            data: Parsed ``ytInitialData`` dict.

        Returns:
            The ``contents`` list of the selected tab, or ``None`` if not found.
        """
        return validate.Schema(
            {"contents": {"twoColumnBrowseResultsRenderer": {"tabs": list}}},
            validate.get(("contents", "twoColumnBrowseResultsRenderer", "tabs")),
            validate.filter(lambda tab: (
                tab.get("tabRenderer", {}).get("selected")
                and tab.get("tabRenderer", {}).get("content", {}).get("richGridRenderer", {}).get("contents")
            )),
            validate.get((0, "tabRenderer", "content", "richGridRenderer", "contents")),
        ).validate(data)

    @staticmethod
    def _schema_active_streams(data) -> list[tuple] | None:
        """Extract active (non-upcoming) video IDs and their viewer count runs.

        Skips non-video items (e.g. ``continuationItemRenderer``) and videos
        with ``upcomingEventData`` (scheduled but not yet live).

        Args:
            data: Raw ``richGridRenderer.contents`` list from ``ytInitialData``.

        Returns:
            List of ``(videoId, runs)`` tuples, where ``runs`` is the ``viewCountText.runs`` list.
        """
        return validate.Schema(
            [
                validate.any(
                    validate.all(
                        {"richItemRenderer": {"content": {"videoRenderer": dict}}},
                        validate.get(("richItemRenderer", "content", "videoRenderer")),
                    ),
                    validate.transform(lambda _: None),
                )
            ],
            validate.filter(lambda v: v is not None),
            # Keep only active streams: must have a viewer count and not be scheduled
            validate.filter(lambda v: v.get("viewCountText", {}).get("runs") and not v.get("upcomingEventData")),
            validate.map(lambda v: (v["videoId"], v["viewCountText"]["runs"])),
        ).validate(data)

    @staticmethod
    def _pick_stream(active_streams) -> str:
        """Select a video ID from *active_streams* according to the ``stream`` plugin option.

        Args:
            active_streams: List of ``(videoId, runs)`` tuples as returned by
                :meth:`_schema_active_streams`.

        Returns:
            The selected video ID string.
        """
        stream_pick = StreamSelection(ctx.options.get("stream")).value
        log.debug("Stream pick option: %r, %d candidate(s)", stream_pick, len(active_streams))

        if isinstance(stream_pick, int):
            # Clamp to last if position exceeds available streams
            index = min(stream_pick - 1, len(active_streams) - 1)
            video_id = active_streams[index][0]
        elif stream_pick == StreamPick.FIRST:
            video_id = active_streams[0][0]
        elif stream_pick == StreamPick.LAST:
            video_id = active_streams[-1][0]
        else:
            # StreamPick.POPULAR: rank by viewer count, pick the highest
            # Clean /runs/.../text from non-digits and get first number for every stream
            ranked = [
                (vid, int(re.sub(r"\D", "", next(r["text"] for r in runs if re.search(r"\d", r["text"])))))
                for vid, runs in active_streams
            ]
            video_id = max(ranked, key=lambda x: x[1])[0]

        log.debug("Selected video ID: %s", video_id)
        return video_id

    def extract(self, url: str) -> ExtractorResult:
        """Extract the selected live video ID from a ``/streams`` page and redirect.

        Args:
            url: YouTube channel streams URL.

        Returns:
            :class:`ExtractorResult` with ``next`` set to a
            :class:`NextExtractor` pointing at the watch URL.
        """
        initial = self._get_initial_data(url)
        tab_data = self._schema_tab_data(initial)
        active_streams = self._schema_active_streams(tab_data)
        log.debug("Active streams found: %d", len(active_streams) if active_streams else 0)
        video_id = self._pick_stream(active_streams)
        watch_url = f"https://www.youtube.com/watch?v={video_id}"
        log.debug("Redirecting to: %s", watch_url)
        return ExtractorResult(
            next=NextExtractor(
                extractor=ExtractorType.VIDEO,
                url=watch_url,
            )
        )


class LiveExtractor:
    """Resolves a YouTube channel/live URL to a watch URL.

    Fetches the channel page, extracts ``ytInitialData``, and returns a
    :class:`NextExtractor` redirect pointing at the live video.
    """

    valid_url_re = r"https://www\.youtube\.com/(?:@|c(?:hannel)?/|user/)?(?P<id>[^/?\\#&]+)/live"
    extractor_type: ExtractorType = ExtractorType.LIVE

    @staticmethod
    def _get_initial_data(url) -> dict:
        """Fetch and return ``ytInitialData`` from *url*, retrying up to 3 times.

        YouTube occasionally returns a page without ``currentVideoEndpoint``,
        so each attempt checks for that key before accepting the result.

        Args:
            url: Channel live page URL.

        Returns:
            Parsed ``ytInitialData`` dict, or ``{}`` if all attempts fail.
        """
        for attempt in range(1, 4):
            try:
                log.debug("Fetching ytInitialData (attempt %d): %s", attempt, url)
                webpage = ctx.session.http.get(url)
                initial = _get_data_from_regex(webpage, _re_ytInitialData, "ytInitialData")
                if initial and initial.get("currentVideoEndpoint"):
                    log.debug("ytInitialData obtained on attempt %d", attempt)
                    return initial
                log.debug("ytInitialData missing currentVideoEndpoint on attempt %d", attempt)
            except Exception as exc:
                log.error("Error fetching ytInitialData (attempt %d): %s", attempt, exc)
        log.warning("All attempts to fetch ytInitialData failed for: %s", url)
        return {}

    @staticmethod
    def _schema_video_id(data) -> str | None:
        """Extract the live video ID from a parsed ``ytInitialData`` object.

        Args:
            data: Parsed ``ytInitialData`` dict.

        Returns:
            Video ID string, or ``None`` if the expected keys are absent.
        """
        return validate.Schema(
            {
                "currentVideoEndpoint": {
                    "watchEndpoint": {"videoId": str},
                },
            },
            validate.get(("currentVideoEndpoint", "watchEndpoint", "videoId")),
        ).validate(data)

    def extract(self, url: str) -> ExtractorResult:
        """Extract the live video ID from a channel/live page and redirect.

        Args:
            url: YouTube channel/live URL (any supported variant).

        Returns:
            :class:`ExtractorResult` with ``next`` set to a
            :class:`NextExtractor` pointing at the watch URL.

        Raises:
            ValueError: If no video ID could be found after all retries.
        """
        url = urlunparse(urlparse(url)._replace(netloc="www.youtube.com"))
        log.debug("TabExtractor.extract: normalised URL -> %s", url)
        initial = self._get_initial_data(url)
        if video_id := self._schema_video_id(initial):
            watch_url = f"https://www.youtube.com/watch?v={video_id}"
            log.debug("Resolved video ID %s, redirecting to %s", video_id, watch_url)
            return ExtractorResult(
                next=NextExtractor(
                    extractor=ExtractorType.VIDEO,
                    url=watch_url
                )
            )
        raise ValueError("Unable to extract video ID from /live page")


class VideoExtractor:
    """Extracts HLS manifest URLs from a YouTube watch page.

    Queries the ``/player`` endpoint for each configured client,
    collects ``hlsManifestUrl`` values, and solves any ``n``-parameter
    challenges via the injected :class:`JsSolver`.
    """

    valid_url_re = r"https://www\.youtube\.com/watch\?v=(?P<id>[0-9A-Za-z_-]{11})"
    extractor_type = ExtractorType.VIDEO

    _re_ytcfg = re.compile(r"ytcfg\.set\s*\(\s*({.+?})\s*\)\s*;")
    _re_ytInitialPlayerResponse = re.compile(r"var\s+ytInitialPlayerResponse\s*=\s*({.+?});\s*(?:var|</script>)")

    video_id: str = None

    def _get_webpage_data(self, url: str) -> dict:
        """Fetch the watch page and return the parsed ``ytcfg`` object.

        Sets the session ``User-Agent`` to the ``web_safari`` value so that
        YouTube serves the standard desktop page layout.

        Args:
            url: Full watch URL including the ``v=`` parameter.

        Returns:
            Parsed ``ytcfg`` dict extracted from the page source.
        """
        log.debug("Fetching watch page: %s", url)
        ctx.session.http.headers["User-Agent"] = CLIENTS["web_safari"]["INNERTUBE_CONTEXT"]["client"]["userAgent"]
        webpage = ctx.session.http.get(url, params={"bpctr": "9999999999", "has_verified": "1"})
        return _get_data_from_regex(webpage, self._re_ytcfg, "ytcfg")

    @staticmethod
    def _build_headers(client_config: dict, visitor_data: str, client_context: dict) -> dict:
        """Assemble HTTP headers for an InnerTube ``/player`` request.

        Falls back to the static client config when the live page context does
        not carry ``clientVersion`` or ``userAgent``.

        Args:
            client_config:  Entry from :data:`CLIENTS` for the current client.
            visitor_data:   ``X-Goog-Visitor-Id`` token extracted from ytcfg.
            client_context: ``client`` sub-dict from the resolved InnerTube context.

        Returns:
            Dict of HTTP headers with ``None`` values removed.
        """
        default_client = client_config.get("INNERTUBE_CONTEXT", {}).get("client", {})
        client_version = client_context.get("clientVersion") or default_client.get("clientVersion")
        ua = client_context.get("userAgent") or default_client.get("userAgent")
        return {
            k: v for k, v in {
                "X-YouTube-Client-Name": str(client_config.get("INNERTUBE_CONTEXT_CLIENT_NAME")),
                "X-YouTube-Client-Version": client_version,
                "Origin": "https://www.youtube.com",
                "X-Goog-Visitor-Id": visitor_data,
                "User-Agent": ua,
                "content-type": "application/json",
            }.items() if v is not None
        }

    def _build_player_request_payload(self, client_context: dict, webpage_ytcfg: dict) -> dict:
        """Build the JSON body for ``/player`` POST request.

        Args:
            client_context: ``client`` sub-dict from the resolved context.
            webpage_ytcfg:  Parsed ``ytcfg`` from the webpage.

        Returns:
            Dict ready to be serialized as the POST body.
        """
        return {
            "context": client_context,
            "videoId": self.video_id,
            "playbackContext": {
                "contentPlaybackContext": {
                    "html5Preference": "HTML5_PREF_WANTS",
                    **({"signatureTimestamp": sts} if (sts := webpage_ytcfg.get("STS")) else {}),
                },
            },
            "contentCheckOk": True,
            "racyCheckOk": True,
        }

    def _extract_player_response(self, client: str, webpage_ytcfg: dict, visitor_data: str) -> dict:
        """Call the ``/player`` endpoint for *client* and return the response.

        Prefers the context embedded in *webpage_ytcfg* over default values
        then overrides locale/timezone fields to ensure
        consistent responses.

        Args:
            client:        Key into :data:`CLIENTS` (e.g. ``"web_safari"``).
            webpage_ytcfg: Parsed ``ytcfg`` from the watch page.
            visitor_data:  Visitor token for the ``X-Goog-Visitor-Id`` header.

        Returns:
            Parsed JSON response from the ``/player`` endpoint.
        """

        # Prefer live page context; fall back to static client config.
        client_config = CLIENTS[client].copy()
        context = webpage_ytcfg.get("INNERTUBE_CONTEXT") or client_config.get("INNERTUBE_CONTEXT", {})
        client_context = context.get("client", {})
        client_context.update({"hl": "en", "timeZone": "UTC", "utcOffsetMinutes": 0})

        headers = self._build_headers(client_config, visitor_data, client_context)
        payload = self._build_player_request_payload(context, webpage_ytcfg)
        response = ctx.session.http.post(
            "https://www.youtube.com/youtubei/v1/player",
            params={"prettyPrint": "false"},
            headers=headers,
            data=json.dumps(payload).encode("utf-8"),
        )
        return response.json()

    @staticmethod
    def _schema_visitor_data(data) -> str:
        """Extract the visitor-data token from a parsed ``ytcfg`` object.

        Accepts either the top-level ``VISITOR_DATA`` key or the nested
        ``INNERTUBE_CONTEXT.client.visitorData`` path.

        Args:
            data: Parsed ``ytcfg`` dict.

        Returns:
            Visitor-data string.
        """
        return validate.Schema(
            validate.any(
                validate.all({"VISITOR_DATA": str}, validate.get("VISITOR_DATA")),
                validate.all(
                    {"INNERTUBE_CONTEXT": {"client": {"visitorData": str}}},
                    validate.get(("INNERTUBE_CONTEXT", "client", "visitorData")),
                ),
            ),
        ).validate(data)

    @staticmethod
    def _schema_player_url(data) -> str:
        """Extract and normalize the JS player URL from a parsed ``ytcfg`` object.

        Accepts either ``PLAYER_JS_URL`` or the first ``jsUrl`` found inside
        ``WEB_PLAYER_CONTEXT_CONFIGS``, and prepends the YouTube origin when
        the URL is relative.

        Args:
            data: Parsed ``ytcfg`` dict.

        Returns:
            Absolute player JS URL.
        """
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
                else f"https://www.youtube.com{url}"
            ),
        ).validate(data)

    def _extract_player_responses(self, webpage_ytcfg: dict) -> tuple[list[dict], str]:
        """Query all configured clients and collect valid player responses.

        Iterates `CLIENTS` in reverse insertion order (``android_vr`` first)
        so that the client most likely to return unthrottled streams is tried first.

        Args:
            webpage_ytcfg: Parsed ``ytcfg`` from the watch page.

        Returns:
            Tuple of ``(player_responses, player_url)`` where *player_responses*
            is a list of dicts that each contain a ``streamingData`` key.

        Raises:
            ValueError: If no client returns a response with ``streamingData``.
        """
        player_responses = []
        visitor_data = self._schema_visitor_data(webpage_ytcfg)
        player_url = self._schema_player_url(webpage_ytcfg)
        log.debug("Player JS URL: %s", player_url)

        for client in reversed(list(CLIENTS)):
            try:
                response = self._extract_player_response(client, webpage_ytcfg, visitor_data)
            except Exception as exc:
                log.error("Player request failed for client %s: %s", client, exc)
                continue

            if not response:
                log.debug("Empty player response for client %s, skipping", client)
                continue

            if not response.get("streamingData"):
                log.warning("No streamingData in player response for client %s", client)
                continue

            log.debug("Valid player response received for client %s", client)
            player_responses.append(response)

        if not player_responses:
            raise ValueError("Failed to extract any player response with streamingData")

        return player_responses, player_url

    @staticmethod
    def _extract_hls(player_responses: list[dict], player_url: str) -> list[str]:
        """Collect HLS manifest URLs from *player_responses*, solving n-challenges.

        For each manifest URL that contains an ``/n/<token>/`` path segment,
        the token is submitted to the injected `JsSolver`.
        URLs whose challenge cannot be solved are dropped with a warning.

        Args:
            player_responses: List of InnerTube player response dicts.
            player_url:       Absolute URL of the player JS bundle used by the solver.

        Returns:
            List of HLS manifest URLs.
        """
        hls_list = []

        for response in player_responses:
            streaming_data = response.get("streamingData")
            if not streaming_data:
                log.debug("Skipping player response with no streamingData")
                continue

            hls_manifest_url = streaming_data.get("hlsManifestUrl")
            if not hls_manifest_url:
                log.debug("No hlsManifestUrl in streamingData: %s", streaming_data)
                continue

            # Solve the n-parameter challenge embedded in the manifest path.
            if n_matches := re.findall(r"/n/([^/]+)/", urlparse(hls_manifest_url).path):
                n_token = n_matches[0]
                log.debug("Solving n-challenge token: %s", n_token)
                result = ctx.deno.solve(NChallengeInput(token=n_token, player_url=player_url))

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

    def extract(self, url: str) -> ExtractorResult:
        """Extract HLS manifest URLs from a YouTube watch URL, retrying up to 3 times.

        Args:
            url: Full ``/watch?v=<id>`` URL.

        Returns:
            :class:`ExtractorResult` with ``hls`` set to the list of resolved manifest URLs.
        """
        hls: list[str] = []

        for attempt in range(1, 4):
            time.sleep(1)
            self.video_id = re.search(self.valid_url_re, url).group("id")
            log.debug("VideoExtractor.extract attempt %d — video_id: %s", attempt, self.video_id)

            webpage_ytcfg = self._get_webpage_data(url)

            try:
                player_responses, player_url = self._extract_player_responses(webpage_ytcfg)
            except ValueError as exc:
                log.error("Player response extraction failed (attempt %d): %s", attempt, exc)
                continue

            hls = self._extract_hls(player_responses, player_url)
            if hls:
                log.debug("HLS extraction succeeded")
                break
            log.warning("No HLS URLs on attempt %d, retrying", attempt)

        return ExtractorResult(hls=hls)
