#!/usr/bin/env python3

from livestreamer.plugins import Plugin, register_plugin
from livestreamer.utils import CommandLine
from livestreamer.compat import urllib, str

import xml.dom.minidom, re, sys, random

class JustinTV(object):
    StreamInfoURL = "http://usher.justin.tv/find/{0}.xml?type=any&p={1}"
    SWFURL = "http://www.justin.tv/widgets/live_embed_player.swf"

    def can_handle_url(self, url):
        return ("justin.tv" in url) or ("twitch.tv" in url)

    def get_channel_name(self, url):
        fd = urllib.urlopen(url)
        data = fd.read()
        fd.close()

        match = re.search(b"live_facebook_embed_player\.swf\?channel=(\w+)", data)
        if match:
            return str(match.group(1), "ascii")


    def get_streams(self, url):
        def get_node_text(element):
            res = []
            for node in element.childNodes:
                if node.nodeType == node.TEXT_NODE:
                    res.append(node.data)
            return "".join(res)

        def clean_tag(tag):
            if tag[0] == "_":
                return tag[1:]
            else:
                return tag

        randomp = int(random.random() * 999999)
        channelname = self.get_channel_name(url)

        if not channelname:
            return False

        fd = urllib.urlopen(self.StreamInfoURL.format(channelname, randomp))
        data = fd.read()
        fd.close()

        # fix invalid xml
        data = re.sub(b"<(\d+)", b"<_\g<1>", data)
        data = re.sub(b"</(\d+)", b"</_\g<1>", data)

        streams = {}
        dom = xml.dom.minidom.parseString(data)
        nodes = dom.getElementsByTagName("nodes")[0]

        for node in nodes.childNodes:
            stream = {}
            for child in node.childNodes:
                stream[child.tagName] = get_node_text(child)

            sname = clean_tag(node.tagName)
            streams[sname] = stream

        return streams

    def stream_cmdline(self, stream, filename):
        cmd = CommandLine("rtmpdump")
        cmd.arg("rtmp", ("{0}/{1}").format(stream["connect"], stream["play"]))
        cmd.arg("swfUrl", self.SWFURL)
        cmd.arg("live", True)
        cmd.arg("flv", filename)

        if "token" in stream:
            cmd.arg("jtv", stream["token"])

        return cmd.format()


register_plugin("justintv", JustinTV)
