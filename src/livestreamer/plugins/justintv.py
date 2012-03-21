#!/usr/bin/env python3

from livestreamer.plugins import Plugin, register_plugin
from livestreamer.stream import RTMPStream
from livestreamer.utils import swfverify
from livestreamer.compat import urllib, str

import xml.dom.minidom, re, sys, random

class JustinTV(Plugin):
    StreamInfoURL = "http://usher.justin.tv/find/{0}.xml?type=any&p={1}"
    StreamInfoURLSub = "http://usher.justin.tv/find/{0}.xml?type=any&p={1}&b_id=true&chansub_guid={2}&private_code=null&group=&channel_subscription={2}"
    MetadataURL = "http://www.justin.tv/meta/{0}.xml?on_site=true"
    SWFURL = "http://www.justin.tv/widgets/live_embed_player.swf"

    @classmethod
    def can_handle_url(self, url):
        return ("justin.tv" in url) or ("twitch.tv" in url)

    @classmethod
    def handle_parser(self, parser):
        parser.add_argument("--jtv-cookie", metavar="cookie", help="JustinTV cookie to allow access to subscription channels")

    def _get_channel_name(self, url):
        fd = urllib.urlopen(url)
        data = fd.read()
        fd.close()

        match = re.search(b"live_facebook_embed_player\.swf\?channel=(\w+)", data)
        if match:
            return str(match.group(1), "ascii")

    def _get_metadata(self, channel, cookie=None):
        if cookie:
            headers = {"Cookie": cookie}
            req = urllib.Request(self.MetadataURL.format(channel), headers=headers)
        else:
            req = urllib.Request(self.MetadataURL.format(channel))


        fd = urllib.urlopen(req)
        data = fd.read()
        fd.close()

        dom = xml.dom.minidom.parseString(data)
        meta = dom.getElementsByTagName("meta")[0]
        metadata = {}

        metadata["title"] = self._get_node_if_exists(dom, "title")
        metadata["chansub_guid"] = self._get_node_if_exists(dom, "chansub_guid")

        return metadata

    def _get_node_if_exists(self, dom, name):
        elements = dom.getElementsByTagName(name)
        if elements and len(elements) > 0:
            return self._get_node_text(elements[0])

    def _get_node_text(self, element):
        res = []
        for node in element.childNodes:
            if node.nodeType == node.TEXT_NODE:
                res.append(node.data)
        return "".join(res)

    def get_streams(self):
        def clean_tag(tag):
            if tag[0] == "_":
                return tag[1:]
            else:
                return tag

        randomp = int(random.random() * 999999)
        channelname = self._get_channel_name(self.url)

        if not channelname:
            return False

        metadata = self._get_metadata(channelname, self.args.jtv_cookie)

        if "chansub_guid" in metadata:
            fd = urllib.urlopen(self.StreamInfoURLSub.format(channelname, randomp, metadata["chansub_guid"]))
        else:
            fd = urllib.urlopen(self.StreamInfoURL.format(channelname, randomp))

        data = fd.read()
        fd.close()

        # fix invalid xml
        data = re.sub(b"<(\d+)", b"<_\g<1>", data)
        data = re.sub(b"</(\d+)", b"</_\g<1>", data)

        streams = {}
        dom = xml.dom.minidom.parseString(data)
        nodes = dom.getElementsByTagName("nodes")[0]

        swfhash, swfsize = swfverify(self.SWFURL)

        for node in nodes.childNodes:
            info = {}
            for child in node.childNodes:
                info[child.tagName] = self._get_node_text(child)

            stream = RTMPStream({
                "rtmp": ("{0}/{1}").format(info["connect"], info["play"]),
                "swfUrl": self.SWFURL,
                "swfhash": swfhash,
                "swfsize": swfsize,
                "live": 1
            })

            if "token" in info:
                stream.params["jtv"] = info["token"]

            sname = clean_tag(node.tagName)
            streams[sname] = stream

        return streams

register_plugin("justintv", JustinTV)
