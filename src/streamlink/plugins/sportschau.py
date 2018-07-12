import re
import json

from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.stream import HDSStream
from streamlink.utils import update_scheme

_url_re = re.compile(r"http(s)?://(\w+\.)?sportschau.de/")
_player_js = re.compile(r"https?://deviceids-medp.wdr.de/ondemand/.*\.js")


class sportschau(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_streams(self):
        res = http.get(self.url)
        match = _player_js.search(res.text)
        if match:
            player_js = match.group(0)
            self.logger.info("Found player js {0}", player_js)
        else:
            self.logger.info("Didn't find player js. Probably this page doesn't contain a video")
            return

        res = http.get(player_js)

        jsonp_start = res.text.find('(') + 1
        jsonp_end = res.text.rfind(')')

        if jsonp_start <= 0 or jsonp_end <= 0:
            self.logger.info("Couldn't extract json metadata from player.js: {0}", player_js)
            return

        json_s = res.text[jsonp_start:jsonp_end]

        stream_metadata = json.loads(json_s)

        hds_url = stream_metadata['mediaResource']['dflt']['videoURL']
        hds_url = update_scheme(self.url, hds_url)

        return HDSStream.parse_manifest(self.session, hds_url).items()


__plugin__ = sportschau
