from livestreamer.exceptions import NoStreamsError
from livestreamer.plugin import Plugin
from livestreamer.stream import RTMPStream, HLSStream
from livestreamer.utils import parse_json, rtmpparse, swfdecompress, urlget

import re

class DMCloud(Plugin):

    @classmethod
    def can_handle_url(self, url):
        return "api.dmcloud.net" in url

    def _get_rtmp_streams(self, swfurl):
        if not RTMPStream.is_usable(self.session):
            raise NoStreamsError(self.url)

        self.logger.debug("Fetching RTMP stream info")

        res = urlget(swfurl)
        swf = swfdecompress(res.content)
        match = re.search("customURL[^h]+(https://.*?)\\\\", swf)

        if not match:
            raise NoStreamsError(self.url)

        res = urlget(match.group(1))
        rtmp, playpath = rtmpparse(res.text)

        params = {
            "rtmp": rtmp,
            "pageUrl": self.url,
            "playpath": playpath,
            "live": True
        }

        match = re.search("file[^h]+(https?://.*?.swf)", swf)
        if match:
            params["swfUrl"] = match.group(1)

        return RTMPStream(self.session, params)

    def _get_streams(self):
        self.logger.debug("Fetching stream info")
        res = urlget(self.url)

        match = re.search("var info = (.*);", res.text)
        if not match:
            raise NoStreamsError(self.url)

        json = parse_json(match.group(1))
        if not isinstance(json, dict):
            return

        ios_url = json.get("ios_url")
        swf_url = json.get("swf_url")
        streams = {}

        if ios_url:
            hls = HLSStream.parse_variant_playlist(self.session, ios_url)
            streams.update(hls)

        if swf_url:
            try:
                streams["live"] = self._get_rtmp_streams(swf_url)
            except NoStreamsError:
                pass

        return streams


__plugin__ = DMCloud
