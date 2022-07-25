"""
$description Global live streaming and video on-demand hosting platform.
$url livestream.com
$type live
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)

URL_API = "https://api.new.livestream.com/accounts/{}/events"


@pluginmatcher(re.compile(
    r"https?://(?:api\.new\.)?livestream\.com/accounts/(?:(\w+))"
))


class Livestream(Plugin):

    def _get_streams(self):
        # If the channel is "hidden", you will most likely be with a precise api.new.livestream.com JSON url,
        # including event number (only getting into the /events endpoint will show an almost blank JSON, no stream attached).
        # This workaround permits you to get access to the hidden streams via Streamlink.
        if self.url.__contains__("api.new."):
            res = self.session.http.get(self.url).json()
        else:
            account_no = self.match.group(2)
            res = self.session.http.get(URL_API.format(account_no)).json()

        # API verification from given URL if there's a live event / working VOD stream.
        if "stream_info" not in res:
            log.debug("No stream has been found with this URL.")
            return
        
        stream_info = res["stream_info"]

        log.debug("stream_info: {0!r}".format(stream_info))
        if not (stream_info and stream_info["is_live"]):
            log.debug("Stream might be Off Air")
            return

        m3u8_url = stream_info.get("secure_m3u8_url")
        if m3u8_url:
            yield from HLSStream.parse_variant_playlist(self.session, m3u8_url).items()
        else:
            log.debug("Unable to find URL.")


__plugin__ = Livestream
