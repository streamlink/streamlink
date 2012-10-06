from livestreamer.compat import str
from livestreamer.options import Options
from livestreamer.plugins import Plugin, PluginError, NoStreamsError
from livestreamer.stream import RTMPStream
from livestreamer.utils import urlget, urlresolve

import re
import random
import xml.dom.minidom

class JustinTV(Plugin):
    options = Options({
        "cookie": None
    })

    StreamInfoURL = "http://usher.justin.tv/find/{0}.xml"
    MetadataURL = "http://www.justin.tv/meta/{0}.xml?on_site=true"
    SWFURL = "http://www.justin.tv/widgets/live_embed_player.swf"

    @classmethod
    def can_handle_url(self, url):
        return ("justin.tv" in url) or ("twitch.tv" in url)

    def _get_channel_name(self, url):
        return url.rstrip("/").rpartition("/")[2].lower()

    def _get_metadata(self):
        url = self.MetadataURL.format(self.channelname)

        headers = {}
        cookie = self.options.get("cookie")

        if cookie:
            headers["Cookie"] = cookie

        res = urlget(url, headers=headers)

        try:
            dom = xml.dom.minidom.parseString(res.text)
        except Exception as err:
            raise PluginError(("Unable to parse config XML: {0})").format(err))

        meta = dom.getElementsByTagName("meta")[0]
        metadata = {}

        metadata["title"] = self._get_node_if_exists(dom, "title")
        metadata["access_guid"] = self._get_node_if_exists(dom, "access_guid")
        metadata["login"] = self._get_node_if_exists(dom, "login")

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

        if len(res) == 0:
            return None
        else:
            return "".join(res)

    def _authenticate(self):
        chansub = None

        if self.options.get("cookie") is not None:
            self.logger.info("Attempting to authenticate using cookies")

            metadata = self._get_metadata()
            chansub = metadata["access_guid"]

            if "login" in metadata and metadata["login"] is not None:
                self.logger.info("Successfully logged in as {0}", metadata["login"])

        return chansub

    def _get_streaminfo(self):
        def clean_tag(tag):
            if tag[0] == "_":
                return tag[1:]
            else:
                return tag

        chansub = self._authenticate()

        url = self.StreamInfoURL.format(self.channelname)
        params = dict(b_id="true", group="", private_code="null",
                      p=int(random.random() * 999999),
                      channel_subscription=chansub, type="any")

        self.logger.debug("Fetching stream info")
        res = urlget(url, params=params)
        data = res.text

        # fix invalid xml
        data = re.sub("<(\d+)", "<_\g<1>", data)
        data = re.sub("</(\d+)", "</_\g<1>", data)

        streams = {}

        try:
            dom = xml.dom.minidom.parseString(data)
        except Exception as err:
            raise PluginError(("Unable to parse config XML: {0})").format(err))

        nodes = dom.getElementsByTagName("nodes")[0]

        if len(nodes.childNodes) == 0:
            return streams

        swfurl = urlresolve(self.SWFURL)

        for node in nodes.childNodes:
            info = {}
            for child in node.childNodes:
                info[child.tagName] = self._get_node_text(child)

            if not ("connect" in info and "play" in info):
                continue

            stream = RTMPStream(self.session, {
                "rtmp": ("{0}/{1}").format(info["connect"], info["play"]),
                "swfVfy": swfurl,
                "live": True
            })

            sname = clean_tag(node.tagName)

            if "token" in info:
                stream.params["jtv"] = info["token"]
            else:
                self.logger.warning("No token found for stream {0}, this stream may fail to play", sname)

            streams[sname] = stream

        return streams

    def _get_streams(self):
        self.channelname = self._get_channel_name(self.url)

        if not self.channelname:
            raise NoStreamsError(self.url)

        return self._get_streaminfo()


__plugin__ = JustinTV
