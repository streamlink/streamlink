"""
$description Live and on-demand video service from World Wrestling Entertainment, Inc.
$url network.wwe.com
$type live, vod
$metadata id
$metadata title
$account Required
"""

import logging
import re

from streamlink.plugin import Plugin, pluginargument, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.ffmpegmux import MuxedStream
from streamlink.stream.hls import HLSStream
from streamlink.stream.http import HTTPStream


log = logging.getLogger(__name__)


@pluginmatcher(
    re.compile(r"https?://network\.wwe\.com/(video|live)/(?P<stream_id>\d+)"),
)
@pluginargument(
    "email",
    required=True,
    requires=["password"],
    metavar="EMAIL",
    help="The email associated with your WWE Network account, required to access any WWE Network stream.",
)
@pluginargument(
    "password",
    required=True,
    sensitive=True,
    metavar="PASSWORD",
    help="A WWE Network account password to use with --wwenetwork-email.",
)
class WWENetwork(Plugin):
    _API_LOGIN_URL = "https://dce-frontoffice.imggaming.com/api/v2/login"
    _API_URLS = {
        "video": "https://dce-frontoffice.imggaming.com/api/v4/vod/{0}",
        "live": "https://dce-frontoffice.imggaming.com/api/v4/event/{0}",
    }

    _API_HEADERS = {
        "x-api-key": "857a1e5d-e35e-4fdf-805b-a87b6f8364bf",
        "realm": "dce.wwe",
    }

    def _login(self, email, password):
        success, data = self.session.http.post(
            self._API_LOGIN_URL,
            json={"id": email, "secret": password},
            headers=self._API_HEADERS,
            raise_for_status=False,
            schema=validate.Schema(
                validate.parse_json(),
                validate.any(
                    validate.all(
                        {"messages": [str]},
                        validate.get(("messages", 0)),
                        validate.transform(lambda data: (False, data)),
                    ),
                    validate.all(
                        {"authorisationToken": str},
                        validate.get("authorisationToken"),
                        validate.transform(lambda data: (True, data)),
                    ),
                ),
            ),
        )

        if not success:
            log.error(data)
            return

        return data

    def _get_streams_content(self, content_type, content_id, token):
        success, data = self.session.http.get(
            self._API_URLS.get(content_type).format(content_id),
            acceptable_status=(200, 401, 404),
            params={"includePlaybackDetails": "URL"},
            headers={"Authorization": f"Bearer {token}", **self._API_HEADERS},
            schema=validate.Schema(
                validate.parse_json(),
                validate.any(
                    validate.all(
                        {"messages": [str]},
                        validate.get(("messages", 0)),
                        validate.transform(lambda message: (False, message)),
                    ),
                    validate.all(
                        {
                            "accessLevel": str,
                            validate.optional("id"): int,
                            validate.optional("title"): str,
                            validate.optional("playerUrlCallback"): validate.any(None, validate.url()),
                        },
                        validate.union_get(
                            "accessLevel",
                            "playerUrlCallback",
                            "id",
                            "title",
                        ),
                        validate.transform(lambda data: (True, data)),
                    ),
                ),
            ),
        )

        if not success:
            log.error(data)
            return

        access, playback_url, self.id, self.title = data

        if access != "GRANTED":
            log.error("Paid subscription required for this video")
            return

        if not playback_url:
            log.error("Failed to get playerUrlCallback from response")
            return

        playback_schema = validate.Schema(
            {
                "url": validate.url(),
                validate.optional("subtitles"): validate.none_or_all(
                    [{"language": str, "format": str, "url": validate.url()}],
                    validate.filter(lambda s: s["format"] == "srt"),
                ),
            },
            validate.union_get("url", "subtitles"),
        )

        playback_streams = self.session.http.get(
            playback_url,
            schema=validate.Schema(
                validate.parse_json(),
                {
                    validate.optional("hls"): validate.any(
                        validate.all(
                            validate.list(playback_schema),
                            validate.get(0),
                        ),
                        playback_schema,
                    ),
                },
            ),
        )

        if playback_stream := playback_streams.get("hls"):
            url, subtitles = playback_stream

            if streams := HLSStream.parse_variant_playlist(self.session, url).items():
                if subtitles and self.session.get_option("mux-subtitles"):
                    substreams = {s["language"]: HTTPStream(self.session, s["url"]) for s in subtitles}

                    for quality, stream in streams:
                        yield quality, MuxedStream(self.session, stream, subtitles=substreams)
                else:
                    yield from streams

    def _get_streams(self):
        if token := self._login(self.get_option("email"), self.get_option("password")):
            return self._get_streams_content(*self.match.groups(), token)


__plugin__ = WWENetwork
