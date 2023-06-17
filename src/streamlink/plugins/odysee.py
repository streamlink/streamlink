"""
$description video on-demand and streaming platform built on LBRY. Also is known as a decentralized alternative to YouTube.
$url odysee.com
$type live, vod
"""

import json
import logging
import re
import urllib

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream
from streamlink.stream.http import HTTPStream


log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"""
        https?://(www\.)?odysee.com/@(?P<odyseeHandle>.*)
    """,
    re.VERBOSE,
))
class Odysee(Plugin):
    def _fetch_odysee_livestream(self, lbry_url):
        backend_livestream_data = self.session.http.post(
            url="https://api.na-backend.odysee.com/api/v1/proxy?m=resolve",
            data=json.dumps({
                "jsonrpc": "2.0",
                "method": "resolve",
                "params": {
                    "urls": [lbry_url],
                },
            }),
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "result": {
                        lbry_url: dict,
                    },
                },
                validate.get("result"),
                validate.get(lbry_url),
            ),
        )

        if "error" in backend_livestream_data:
            backend_error = backend_livestream_data["error"]
            if type(backend_error) is str:
                log.error(f"Odysee returned an error: {backend_error}")
                return None
            odysee_error = backend_error["name"]
            if odysee_error == "NOT_FOUND":
                log.error("Odysee livestream url is not found 404.")
            else:
                log.error(f"Odysee backend returned an error: {odysee_error}")
            return None
        channel_claim_id = backend_livestream_data["signing_channel"]["claim_id"]
        # Check whether the livestream is online.
        livestream_api_data = self.session.http.post(
            url="https://api.odysee.live/livestream/is_live", data={"channel_claim_id": channel_claim_id},
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "error": validate.any(str, None),
                    "data": validate.any({
                        "Live": bool,
                        "VideoURL": str,
                    }, None),
                },
            ),
        )
        error = livestream_api_data["error"]
        if error is not None:
            log.error(f"""An error occured while checking whether the url is a livestream or not: {error}""")
            return None
        if livestream_api_data["data"] is None:
            log.error("""Odysee livestream backend returned empty data.""")
            return None
        is_live = livestream_api_data["data"]["Live"]
        if not is_live:
            log.error("Currently odysee livestream is offline.")
            return None
        return livestream_api_data["data"]["VideoURL"]

    def _fetch_odysee_vid(self, lbry_url):
        video_data = self.session.http.post(
            url="https://api.na-backend.odysee.com/api/v1/proxy?m=get",
            data=json.dumps({
                "jsonrpc": "2.0",
                "method": "get",
                "params": {
                    "uri":  lbry_url,
                    "environment": "live",
                },
            }),
            schema=validate.Schema(
                validate.parse_json(),
                validate.any({
                    "result": {
                        "streaming_url": str,
                    },
                }, {
                    "error": {
                        "code": int,
                        "message": str,
                    },
                }),
            ),
        )
        if "error" in video_data:
            video_data_error = video_data["error"]
            if video_data_error["message"] == "couldn't find claim":
                log.error("Odysee video URL is not found 404.")
                return None
            if video_data_error["message"] != "stream doesn't have source data":
                log.error("Odysee backend returned unexpected error.")
                log.error(f"Error code: {video_data_error['code']}")
                log.error(f"Error message: {video_data_error['message']}")
                return None
            # Otherwise the given URL is a livestream.
        else:
            # URL is a video.
            return video_data["result"]["streaming_url"]
        return None

    def _vid_stream_generator(self, odysee_vid_stream):
        yield "live", HTTPStream(self.session, odysee_vid_stream)

    def _get_streams(self):
        obyseeHandle = self.match.group("odyseeHandle")
        odyseeHandle = "@" + obyseeHandle.replace(":", "#")
        lbry_url = f"lbry://{odyseeHandle}"
        lbry_url = urllib.parse.unquote(lbry_url).rstrip("/")
        self.session.http.headers.update({"Referer": "https://odysee.com/"})

        odysee_vid_stream = self._fetch_odysee_vid(lbry_url)
        if odysee_vid_stream is not None:
            print(odysee_vid_stream)
            return self._vid_stream_generator(odysee_vid_stream)
        else:
            odysee_livestream_url = self._fetch_odysee_livestream(lbry_url)
            if odysee_livestream_url is not None:
                return HLSStream.parse_variant_playlist(self.session, odysee_livestream_url)

__plugin__ = Odysee
