"""
$description TikTok is a short-form video hosting service owned by ByteDance
$url www.tiktok.com
$type live
"""
import re
import logging
import streamlink.plugin
import streamlink.stream

from streamlink.exceptions import NoStreamsError, PluginError
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.http import HTTPStream
from streamlink.stream.hls import HLSStream, HLSStreamReader, HLSStreamWorker, HLSStreamWriter
from streamlink.stream.hls_playlist import M3U8, ByteRange, DateRange, ExtInf, Key, M3U8Parser, Map, load as load_hls_playlist
import requests

log = logging.getLogger(__name__)


@pluginmatcher(
    pattern=re.compile(
        r"https?://(?:www\.)?tiktok\.com/@(?P<channel>[^/]+)/live?"),
)
class TikTok(Plugin):
    url_re = re.compile(
        r"https?://(?:www\.)?tiktok\.com/@(?P<channel>[^/]+)/live?$")
    
    _QUALITY_MAP = {
        "hd_60": "720p60",
        "hd": "720p",
        "sd": "540p",
        "ld": "360p",
    }

    def _get_media(self):
        try:
            media = self.session.http.get(self.url, schema=validate.Schema(
                validate.parse_html(),
                validate.xml_xpath_string(
                    ".//script[@id='SIGI_STATE']"),
                validate.parse_json(),
                validate.get('LiveRoom'),
                validate.get('liveRoomUserInfo'),
                validate.get('liveRoom'),
                validate.get('hevcStreamData'),
                validate.get('pull_data'),
                validate.get('stream_data'),
                validate.parse_json(),
                validate.get("data"),
                validate.all(
                    {
                        "hd": validate.all(
                            validate.get("main"),
                            validate.get("hls"),
                            validate.any(None, validate.url())
                        ),
                        "sd": validate.all(
                            validate.get("main"),
                            validate.get("hls"),
                            validate.any(None, validate.url())
                        ),
                        "ld": validate.all(
                            validate.get("main"),
                            validate.get("hls"),
                            validate.any(None, validate.url())
                        ),
                        "hd_60": validate.all(
                            validate.get("main"),
                            validate.get("hls"),
                            validate.any(None, validate.url())
                        ),
                        "origin": validate.all(
                            validate.get("main"),
                            validate.get("hls"),
                            validate.any(None, validate.url())
                        ),
                    },
                    validate.transform(dict)
                ),
            ))
            return media
        except (PluginError, TypeError):
            pass

        return None

    def _get_streams(self):

        media = self._get_media()

        if not media:
            return
        
        self.session.http.headers.update({
            "referer": self.url,
            "origin": self.url,
        })

        self.logger.info("Stream status: {0}".format("active"))
        
        for quality, stream in media.items():
          yield self._QUALITY_MAP.get(quality, quality), HLSStream(self.session, stream)

__plugin__ = TikTok
