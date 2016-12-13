from __future__ import print_function

import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.plugin.api import validate
from streamlink.stream import HDSStream
from streamlink.stream import HLSStream


class StarTVBase(Plugin):
    """
    Base class for all StarTV streams
    """
    url_re = None
    hds_schema = validate.Schema(validate.all(
        {
            "success": True,
            "xtra": {
                "url": validate.url(),
                "use_akamai": bool
            }
        },
        validate.get("xtra")
    ))
    SWF_URL = "http://dygassets.akamaized.net/player2/plugins/flowplayer/flowplayer.httpstreaming-3.2.11.swf"

    @classmethod
    def can_handle_url(cls, url):
        if not cls.url_re:
            raise NotImplementedError
        return cls.url_re.match(url) is not None

    def _get_star_streams(self, desktop_url, mobile_url):
        if mobile_url:
            for s in HLSStream.parse_variant_playlist(self.session,
                                                         mobile_url,
                                                         headers={"Referer": self.url}).items():
                yield s
        if desktop_url:
            # get the HDS stream URL
            res = http.get(desktop_url)
            stream_data = http.json(res, schema=self.hds_schema)
            for s in HDSStream.parse_manifest(self.session,
                                                 stream_data["url"],
                                                 pvswf=self.SWF_URL,
                                                 is_akamai=stream_data["use_akamai"],
                                                 headers={"Referer": self.url}).items():
                yield s


class StarTV(StarTVBase):
    """
    Support for the Live Stream from www.startv.com.tr, both HLS and HDS streams
    """
    url_re = re.compile(r"http://www.startv.com.tr/canli-yayin")
    mobile_player = re.compile(r"mobileUrl: \"(.*?)\"")
    desktop_player = re.compile(r"flashUrl: \"(.*?)\"")

    def _get_streams(self):
        res = http.get(self.url)
        mobile_url = self.mobile_player.search(res.text)
        desktop_url = self.desktop_player.search(res.text)
        return self._get_star_streams(desktop_url.group(1), mobile_url.group(1))

__plugin__ = StarTV
