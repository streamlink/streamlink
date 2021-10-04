import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?pandalive\.co\.kr/"
))
class Pandalive(Plugin):
    _room_id_re = re.compile(r"roomid\s*=\s*String\.fromCharCode\((.*)\)")

    def _get_streams(self):
        media_code = self.session.http.get(self.url, schema=validate.Schema(
            validate.parse_html(),
            validate.xml_xpath_string(".//script[contains(text(), 'roomid')]/text()"),
            validate.any(None, validate.all(
                validate.transform(self._room_id_re.search),
                validate.any(None, validate.all(
                    validate.get(1),
                    validate.transform(lambda s: "".join(map(lambda c: chr(int(c)), s.split(",")))),
                )),
            )),
        ))

        if not media_code:
            return

        log.debug("Media code: {0}".format(media_code))

        json = self.session.http.post(
            "https://api.pandalive.co.kr/v1/live/play",
            data={"action": "watch", "mediaCode": media_code},
            schema=validate.Schema(
                validate.parse_json(), {
                    validate.optional("media"): {
                        "title": validate.text,
                        "userId": validate.text,
                        "userNick": validate.text,
                        "isPw": bool,
                        "isLive": bool,
                        "liveType": validate.text,
                    },
                    validate.optional("PlayList"): {
                        "hls2": [{
                            "url": validate.url(),
                        }],
                    },
                    "result": bool,
                    "message": validate.text,
                },
            )
        )

        if not json["result"]:
            log.error(json["message"])
            return

        if not json["media"]["isLive"]:
            log.error("The broadcast has ended")
            return

        if json["media"]["isPw"]:
            log.error("The broadcast is password protected")
            return

        log.info("Broadcast type: {0}".format(json['media']['liveType']))

        self.author = "{0} ({1})".format(json['media']['userNick'], json['media']['userId'])
        self.title = "{0}".format(json['media']['title'])

        return HLSStream.parse_variant_playlist(self.session, json["PlayList"]["hls2"][0]["url"])


__plugin__ = Pandalive
