"""
$description Live TV channels and video on-demand service from ARD, a German public, independent broadcaster.
$url ardmediathek.de
$url mediathek.daserste.de
$type live, vod
$region Germany
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream
from streamlink.stream.http import HTTPStream


log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"""
        https?://(\w+\.)?ardmediathek\.de/
        (?:
            live/(?:[^/]+/)?(?P<id_live>\w+)
            |
            video/(?:[^/]+/[^/]+/[^/]+/)?(?P<id_video>\w+)
        )
        (?:\?|$)
    """,
    re.VERBOSE,
))
class ARDMediathek(Plugin):
    _URL_API = "https://api.ardmediathek.de/page-gateway/pages/ard/item/{item}"
    _QUALITY_MAP = {
        4: "1080p",
        3: "720p",
        2: "540p",
        1: "360p",
        0: "270p",
    }

    def _get_streams(self):
        data_json = self.session.http.get(self.url, schema=validate.Schema(
            validate.parse_html(),
            validate.xml_xpath_string(".//script[@type='application/json'][@id='fetchedContextValue2'][1]/text()"),
            validate.none_or_all(
                validate.parse_json(),
                [validate.list(str, {"data": dict})],
                validate.filter(lambda item: item[0].startswith("https://api.ardmediathek.de/page-gateway/pages/")),
                validate.any(
                    validate.get((0, 1, "data")),
                    [],
                ),
            ),
        ))
        if not data_json:
            data_json = self.session.http.get(
                self._URL_API.format(item=self.match.group("id_live") or self.match.group("id_video")),
                params={
                    "devicetype": "pc",
                    "embedded": "false",
                },
                schema=validate.Schema(validate.parse_json()),
            )
        if not data_json:
            return

        schema_data = validate.Schema({
            "id": str,
            "widgets": validate.all(
                [dict],
                validate.filter(lambda item: item.get("mediaCollection")),
                validate.get(0),
                validate.any(None, validate.all(
                    {
                        "geoblocked": bool,
                        "publicationService": {
                            "name": str,
                        },
                        "show": validate.any(None, validate.all(
                            {"title": str},
                            validate.get("title")
                        )),
                        "title": str,
                        "mediaCollection": {
                            "embedded": {
                                "_mediaArray": [validate.all(
                                    {
                                        "_mediaStreamArray": [validate.all(
                                            {
                                                "_quality": validate.any(str, int),
                                                "_stream": validate.url(),
                                            },
                                            validate.union_get("_quality", "_stream")
                                        )]
                                    },
                                    validate.get("_mediaStreamArray"),
                                    validate.transform(dict)
                                )]
                            }
                        },
                    },
                    validate.union_get(
                        "geoblocked",
                        ("mediaCollection", "embedded", "_mediaArray", 0),
                        ("publicationService", "name"),
                        "title",
                        "show",
                    )
                ))
            )
        })
        data = schema_data.validate(data_json)

        log.debug(f"Found media id: {data['id']}")
        if not data["widgets"]:
            log.info("The content is unavailable")
            return

        geoblocked, media, self.author, self.title, show = data["widgets"]
        if geoblocked:
            log.info("The content is not available in your region")
            return
        if show:
            self.title = f"{show}: {self.title}"

        if media.get("auto"):
            yield from HLSStream.parse_variant_playlist(self.session, media.get("auto")).items()
        else:
            for quality, stream in media.items():
                yield self._QUALITY_MAP.get(quality, quality), HTTPStream(self.session, stream)


__plugin__ = ARDMediathek
