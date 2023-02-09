"""
$description Global live-streaming and video on-demand hosting platform.
$url livestream.com
$type live
"""

import logging
import re
from operator import itemgetter

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"""
        https?://(?P<subdomain>api\.new\.|www\.)?livestream\.com
        /accounts/(?P<account>\d+)
        (?:
            /events/(?P<event>\d+)
            |
            /[^/]+
        )?
        (?:/videos/(?P<video>\d+))?
    """,
    re.VERBOSE,
))
class Livestream(Plugin):
    URL_API_EVENTS = "https://api.new.livestream.com/accounts/{account}/events"
    URL_API_EVENTS_EVENT = "https://api.new.livestream.com/accounts/{account}/events/{event}"
    URL_API_VIDEO = "https://api.new.livestream.com/accounts/{account}/events/{event}/videos/{video}"

    def _get_streams(self):
        subdomain, account, event, video = itemgetter("subdomain", "account", "event", "video")(self.match.groupdict())

        if event is None:
            if video is None or subdomain == "api.new.":
                event = self.session.http.get(
                    self.URL_API_EVENTS.format(account=account),
                    schema=validate.Schema(
                        validate.parse_json(),
                        {"data": [dict]},
                        validate.get(("data", 0)),
                        validate.none_or_all(
                            {"id": int},
                            validate.get("id"),
                        ),
                    ),
                )
            else:
                event = self.session.http.get(
                    self.url,
                    schema=validate.Schema(
                        validate.parse_html(),
                        validate.xml_xpath_string(".//script[contains(text(), 'window.config = ')][1]/text()"),
                        validate.none_or_all(
                            re.compile(r"^window\.config\s*=\s*(\{.+});?\s*$"),
                            validate.none_or_all(
                                validate.get(1),
                                validate.parse_json(),
                                {"event": {"id": int}},
                                validate.get(("event", "id")),
                            ),
                        ),
                    ),
                )
            if event is None:
                log.error("Could not find event ID")
                return

        if video is None:
            self.id, self.title, is_live, m3u8_url = self.session.http.get(
                self.URL_API_EVENTS_EVENT.format(account=account, event=event),
                schema=validate.Schema(
                    validate.parse_json(),
                    {
                        "stream_info": {
                            "broadcast_id": int,
                            validate.optional("stream_title"): validate.any(None, str),
                            "is_live": bool,
                            "secure_m3u8_url": validate.url(path=validate.endswith(".m3u8")),
                        },
                    },
                    validate.get("stream_info"),
                    validate.union_get(
                        "broadcast_id",
                        "stream_title",
                        "is_live",
                        "secure_m3u8_url",
                    ),
                ),
            )
            if not is_live:
                log.error("The stream is not available")
                return

        else:
            self.id, self.title, m3u8_url = self.session.http.get(
                self.URL_API_VIDEO.format(account=account, event=event, video=video),
                schema=validate.Schema(
                    validate.parse_json(),
                    {
                        "id": int,
                        validate.optional("description"): validate.any(None, str),
                        "secure_m3u8_url": validate.url(path=validate.endswith(".m3u8")),
                    },
                    validate.union_get(
                        "id",
                        "description",
                        "secure_m3u8_url",
                    ),
                ),
            )

        yield from HLSStream.parse_variant_playlist(self.session, m3u8_url).items()


__plugin__ = Livestream
