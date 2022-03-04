"""
$url attheshore.com
$type live
"""

import logging
import re

from streamlink.plugin import Plugin, PluginError, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://attheshore\.com/livecam-(.+)"
))
class AtTheShore(Plugin):
    _stream_re = re.compile(r"""(?:<source\s+)(?=src\s*=\s*(?P<quote>["']?)(?P<value>.*?)(?P=quote)\s*)?""", re.DOTALL)
    _videoapi_url = "http://api.igv.com/v1.5/getVideoStream?apiKey=T1iSb7bCmg3UPxKC9pHAg4ykgMGPAjsg&id={camid}"

    _stream_schema = validate.Schema(validate.transform(_stream_re.search), validate.get("value"), validate.url())

    def _get_streams(self):
        try:
            res = self.session.http.get(
                self._videoapi_url.format(camid=self.match.group(1)), headers={"Referer": self.url}, schema=self._stream_schema
            )
        except PluginError as err:
            log.debug(err)
        else:
            if ".m3u8" in res:
                return HLSStream.parse_variant_playlist(self.session, res)


__plugin__ = AtTheShore
