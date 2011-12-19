#!/usr/bin/env python3

from livestreamer.plugins import Plugin, register_plugin
from livestreamer.utils import CommandLine
from livestreamer.compat import urllib

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

    def can_handle_url(self, url):
        return "own3d.tv" in url

    def get_channel_id(self, url):
        fd = urlopener.open(url)
        data = fd.read()
        fd.close()

        match = re.search(b"own3d.tv\/livestreamfb\/(\d+)", data)
        if match:
            return int(match.group(1))

    def get_streams(self, url):
        channelid = self.get_channel_id(url)

        if not channelid:
            return False

        fd = urllib.urlopen(self.ConfigURL.format(channelid))
        data = fd.read()
        fd.close()

        streams = {}
        dom = xml.dom.minidom.parseString(data)
        channels = dom.getElementsByTagName("channels")[0]
        clip = channels.getElementsByTagName("clip")[0]

        streams = {}
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
                    streams[name] = {
                        "base": base,
                        "name": name,
                        "playpath": playpath
                    }

        return streams


    def stream_cmdline(self, stream, filename):
        cmd = CommandLine("rtmpdump")
        cmd.arg("rtmp", ("{0}/{1}").format(stream["base"], stream["playpath"]))
        cmd.arg("live", True)
        cmd.arg("flv", filename)

        return cmd.format()


register_plugin("own3dtv", OwnedTV)
