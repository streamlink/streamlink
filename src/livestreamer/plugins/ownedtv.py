#!/usr/bin/env python3

from livestreamer.compat import urllib
from livestreamer.plugins import Plugin, PluginError, NoStreamsError, register_plugin
from livestreamer.stream import RTMPStream
from livestreamer.utils import urlget

import xml.dom.minidom, re

class RelativeRedirectHandler(urllib.HTTPRedirectHandler):
    def http_error_302(self, req, fp, code, msg, headers):
        if "location" in headers and headers["location"][0] == "/":
            absurl = ("{scheme}://{host}{path}").format(
                      scheme=req.get_type(), host=req.get_host(),
                      path=headers["location"])
            del headers["location"]
            headers["location"] = absurl

        return urllib.HTTPRedirectHandler.http_error_301(
               self, req, fp, code, msg, headers)

urlopener = urllib.build_opener(RelativeRedirectHandler)


class OwnedTV(Plugin):
    ConfigURL = "http://www.own3d.tv/livecfg/{0}"
    CDN = {
        "cdn1": "rtmp://fml.2010.edgecastcdn.net/202010",
        "cdn2": "rtmp://owned.fc.llnwd.net:1935/owned",
        "cdn3": "http://hwcdn.net/u4k2r7c4/fls",
    }

    @classmethod
    def can_handle_url(self, url):
        return "own3d.tv" in url

    def _get_channel_id(self, url):
        data = urlget(url, opener=urlopener)

        match = re.search(b'flashvars.config = "livecfg/(\d+)', data)
        if match:
            return int(match.group(1))

        match = re.search(b"document.location.hash='/live/(\d+)'", data)
        if match:
            return int(match.group(1))

        match = re.search(b"xajax_load_live_config\((\d+),", data)
        if match:
            return int(match.group(1))

    def _get_streams(self):
        channelid = self._get_channel_id(self.url)

        if not channelid:
            raise NoStreamsError(self.url)

        data = urlget(self.ConfigURL.format(channelid))

        try:
            dom = xml.dom.minidom.parseString(data)
        except Exception as err:
            raise PluginError(("Unable to parse config XML: {0})").format(err))

        streams = {}
        channels = dom.getElementsByTagName("channels")[0]
        clip = channels.getElementsByTagName("clip")[0]

        for item in clip.getElementsByTagName("item"):
            base = item.getAttribute("base")
            if not base:
                continue

            if base[0] == "$":
                ref = re.match("\${(.+)}", base).group(1)
                base = self.CDN[ref]

            for streamel in item.getElementsByTagName("stream"):
                name = streamel.getAttribute("label").lower().replace(" ", "_")
                playpath = streamel.getAttribute("name")

                if not name in streams:
                    streams[name] = RTMPStream({
                        "rtmp": ("{0}/{1}").format(base, playpath),
                        "live": 1
                    })

        return streams

register_plugin("own3dtv", OwnedTV)
