import re
import json

from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http
from livestreamer.stream import HDSStream

_url_re = re.compile("http(s)?://(\w+\.)?sportschau.de/")
_player_js = re.compile("https?://deviceids-medp.wdr.de/ondemand/.*\.js")

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

        # ensure utf8        
        response_text = res.text.encode('utf-8')

        jsonp_start = response_text.find('(') + 1
        jsonp_end = response_text.rfind(')')

        if jsonp_start <= 0 or jsonp_end <= 0:
            self.logger.info("Couldn't extract json metadata from player.js: {0}", player_js)
            return
            
        json_s = response_text[jsonp_start:jsonp_end]
        
        stream_metadata = json.loads(json_s)
        self.logger.info("Metadata: {0}", stream_metadata)
        
        return HDSStream.parse_manifest(self.session, stream_metadata['mediaResource']['dflt']['videoURL']).items()

__plugin__ = sportschau
