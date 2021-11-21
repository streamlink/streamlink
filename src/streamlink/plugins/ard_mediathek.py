import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:(\w+\.)?ardmediathek\.de/|mediathek\.daserste\.de/)"
))
class ARDMediathek(Plugin):
    def _get_streams(self):
        data_json = self.session.http.get(self.url, schema=validate.Schema(
            validate.parse_html(),
            validate.xml_findtext(".//script[@id='fetchedContextValue'][@type='application/json']"),
            validate.any(None, validate.all(
                validate.parse_json(),
                {str: dict},
                validate.transform(lambda obj: list(obj.items())),
                validate.filter(lambda item: item[0].startswith("https://api.ardmediathek.de/page-gateway/pages/")),
                validate.any(validate.get((0, 1)), [])
            ))
        ))
        if not data_json:
            return

        schema_data = validate.Schema({
            "id": str,
            "widgets": validate.all(
                [dict],
                validate.filter(lambda item: item.get("mediaCollection")),
                validate.get(0),
                {
                    "geoblocked": bool,
                    "publicationService": {
                        "name": str,
                    },
                    "title": str,
                    "mediaCollection": {
                        "embedded": {
                            "_mediaArray": [{
                                "_mediaStreamArray": [{
                                    "_quality": validate.any(str, int),
                                    "_stream": validate.url()
                                }]
                            }]
                        }
                    }
                }
            )
        })
        data = schema_data.validate(data_json)

        log.debug(f"Found media id: {data['id']}")
        data_media = data["widgets"]

        if data_media["geoblocked"]:
            log.info("The content is not available in your region")
            return

        self.author = data_media["publicationService"]["name"]
        self.title = data_media["title"]

        for media in data_media["mediaCollection"]["embedded"]["_mediaArray"]:
            for stream in media["_mediaStreamArray"]:
                if stream["_quality"] != "auto" or ".m3u8" not in stream["_stream"]:
                    continue
                return HLSStream.parse_variant_playlist(self.session, stream["_stream"])


__plugin__ = ARDMediathek
