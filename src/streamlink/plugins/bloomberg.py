"""
$description America-based television network centred towards business and capital market programming.
$url bloomberg.com
$type live, vod
$webbrowser Used as a fallback if their bot-detection prevents access to the stream data.
$metadata title
"""

from __future__ import annotations

import logging
import re

from streamlink.plugin import Plugin, PluginError, pluginmatcher
from streamlink.plugin.api import useragents, validate
from streamlink.stream.hls import HLSStream


log = logging.getLogger(__name__)


@pluginmatcher(
    name="live",
    pattern=re.compile(r"https?://(?:www\.)?bloomberg\.com/live(?:/(?P<channel>[^/]+))?"),
)
@pluginmatcher(
    name="vod",
    pattern=re.compile(r"https?://(?:www\.)?bloomberg\.com/news/videos/[^/]+/[^/]+"),
)
class Bloomberg(Plugin):
    LIVE_API_URL = "https://cdn.gotraffic.net/projector/latest/assets/config/config.min.json?v=1"
    VOD_API_URL = "https://www.bloomberg.com/api/embed?id={0}"
    DEFAULT_CHANNEL = "us"

    _schema_preloaded_state = validate.Schema(
        validate.parse_html(),
        validate.xml_xpath_string(".//script[contains(text(),'window.__PRELOADED_STATE__')][1]/text()"),
        validate.none_or_all(
            re.compile(r"\bwindow\.__PRELOADED_STATE__\s*=\s*(?P<json>{.+?})\s*;(?:\s|$)"),
            validate.none_or_all(
                validate.get("json"),
                validate.parse_json(),
            ),
        ),
    )

    def _get_live_streams(self, data, channel):
        schema_live_ids = validate.Schema(
            {
                "live": {
                    "channels": {
                        "byChannelId": {
                            channel: validate.all(
                                {"liveId": str},
                                validate.get("liveId"),
                            ),
                        },
                    },
                },
            },
            validate.get(("live", "channels", "byChannelId", channel)),
        )
        try:
            live_id = schema_live_ids.validate(data)
        except PluginError:
            log.error(f"Could not find liveId for channel '{channel}'")
            return

        log.debug(f"Found liveId: {live_id}")
        return self.session.http.get(
            self.LIVE_API_URL,
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "livestreams": {
                        live_id: {
                            validate.optional("cdns"): validate.all(
                                [
                                    {
                                        "streams": [
                                            {
                                                "url": validate.url(),
                                            },
                                        ],
                                    },
                                ],
                                validate.transform(lambda x: [urls["url"] for y in x for urls in y["streams"]]),
                            ),
                        },
                    },
                },
                validate.get(("livestreams", live_id, "cdns")),
            ),
        )

    def _get_vod_streams(self, data):
        schema_vod_list = validate.Schema(
            validate.any(
                validate.all(
                    {"video": {"videoStory": dict}},
                    validate.get(("video", "videoStory")),
                ),
                validate.all(
                    {"quicktakeVideo": {"videoStory": dict}},
                    validate.get(("quicktakeVideo", "videoStory")),
                ),
            ),
            {
                "video": {
                    "bmmrId": str,
                },
            },
            validate.get(("video", "bmmrId")),
        )
        schema_url = validate.all(
            {"url": validate.url()},
            validate.get("url"),
        )

        try:
            video_id = schema_vod_list.validate(data)
        except PluginError:
            log.error("Could not find videoId")
            return

        log.debug(f"Found videoId: {video_id}")
        vod_url = self.VOD_API_URL.format(video_id)
        secureStreams, streams, self.title = self.session.http.get(
            vod_url,
            schema=validate.Schema(
                validate.parse_json(),
                {
                    validate.optional("secureStreams"): [schema_url],
                    validate.optional("streams"): [schema_url],
                    "title": str,
                },
                validate.union_get("secureStreams", "streams", "title"),
            ),
        )

        return secureStreams or streams

    def _get_webbrowser(self) -> dict | None:
        import trio  # noqa: I001, PLC0415
        from streamlink.compat import BaseExceptionGroup  # noqa: PLC0415
        from streamlink.webbrowser.cdp import CDPClient, CDPClientSession, devtools  # noqa: PLC0415

        send: trio.MemorySendChannel[str | None]
        receive: trio.MemoryReceiveChannel[str | None]

        data = None
        send, receive = trio.open_memory_channel(1)
        timeout = self.session.get_option("webbrowser-timeout")

        async def on_response(client_session: CDPClientSession, request: devtools.fetch.RequestPaused):
            if request.response_status_code and 300 <= request.response_status_code < 400:
                return await client_session.continue_request(request)

            async with client_session.alter_request(request) as cm:
                await send.send(cm.body)
                cm.body = ""

        async def run(client: CDPClient):
            client_session: CDPClientSession
            async with client.session() as client_session:
                client_session.add_request_handler(on_response, on_request=False)
                with trio.move_on_after(timeout):
                    async with client_session.navigate(self.url) as frame_id:
                        await client_session.loaded(frame_id)
                        return await receive.receive()

        try:
            data = CDPClient.launch(self.session, run)
        except BaseExceptionGroup:
            log.exception(f"Failed requesting {self.url}")
        except Exception as err:
            log.error(err)

        if not data:
            return None

        return self._schema_preloaded_state.validate(data)

    def _get_streams(self):
        self.session.http.headers.clear()
        self.session.http.headers["User-Agent"] = useragents.CHROME

        data = self.session.http.get(self.url, schema=self._schema_preloaded_state)
        if not data:
            log.info("Could not find JSON data. Falling back to webbrowser API...")
            data = self._get_webbrowser()

        if not data:
            log.error("Could not find JSON data. Invalid URL or bot protection...")
            return

        if self.matches["live"]:
            streams = self._get_live_streams(data, self.match["channel"] or self.DEFAULT_CHANNEL)
        else:
            streams = self._get_vod_streams(data)

        if streams:
            # just return the first stream
            return HLSStream.parse_variant_playlist(self.session, streams[0])


__plugin__ = Bloomberg
