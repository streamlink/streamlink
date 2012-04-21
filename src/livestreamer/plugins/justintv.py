#!/usr/bin/env python3

from livestreamer.plugins import Plugin, PluginError, register_plugin
from livestreamer.stream import RTMPStream
from livestreamer.utils import swfverify, urlget
from livestreamer.compat import urllib, str

import xml.dom.minidom, re, sys, random

class JustinTV(Plugin):
    StreamInfoURL = "http://usher.justin.tv/find/{0}.xml?type=any&p={1}"
    StreamInfoURLSub = "http://usher.justin.tv/find/{0}.xml?type=any&p={1}&b_id=true&chansub_guid={2}&private_code=null&group=&channel_subscription={2}"
    MetadataURL = "http://www.justin.tv/meta/{0}.xml?on_site=true"
    SWFURL = "http://www.justin.tv/widgets/live_embed_player.swf"

    cookie = None

    @classmethod
    def can_handle_url(self, url):
        return ("justin.tv" in url) or ("twitch.tv" in url)

    @classmethod
    def handle_parser(self, parser):
        parser.add_argument("--jtv-cookie", metavar="cookie", help="JustinTV cookie to allow access to subscription channels")

    @classmethod
    def handle_args(self, args):
        self.cookie = args.jtv_cookie

    def _get_channel_name(self, url):
        data = urlget(url)
        match = re.search(b"live_facebook_embed_player\.swf\?channel=(\w+)", data)

        if match:
            return str(match.group(1), "ascii")

    def _get_metadata(self, channel):
        if self.cookie:
            headers = {"Cookie": self.cookie}
            req = urllib.Request(self.MetadataURL.format(channel), headers=headers)
        else:
            req = urllib.Request(self.MetadataURL.format(channel))

        data = urlget(req)

        try:
            dom = xml.dom.minidom.parseString(data)
        except Exception as err:
            raise PluginError(("Unable to parse config XML: {0})").format(err))

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

    def _get_streaminfo(self, channelname):
        def clean_tag(tag):
            if tag[0] == "_":
                return tag[1:]
            else:
                return tag

        metadata = self._get_metadata(channelname)
        randomp = int(random.random() * 999999)

        if "chansub_guid" in metadata:
            url = self.StreamInfoURLSub.format(channelname, randomp, metadata["chansub_guid"])
        else:
            url = self.StreamInfoURL.format(channelname, randomp)

        data = urlget(url)

        # fix invalid xml
        data = re.sub(b"<(\d+)", b"<_\g<1>", data)
        data = re.sub(b"</(\d+)", b"</_\g<1>", data)

        streams = {}

        try:
            dom = xml.dom.minidom.parseString(data)
        except Exception as err:
            raise PluginError(("Unable to parse config XML: {0})").format(err))

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

    def _get_streams(self):
        channelname = self._get_channel_name(self.url)

        if not channelname:
            return {}

        return self._get_streaminfo(channelname)

register_plugin("justintv", JustinTV)
