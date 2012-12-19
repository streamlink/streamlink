from livestreamer.compat import bytes, str
from livestreamer.plugins import Plugin, PluginError, NoStreamsError
from livestreamer.stream import RTMPStream
from livestreamer.utils import urlget, res_xml, get_node_text

import re

class OwnedTV(Plugin):
    ConfigURL = "http://www.own3d.tv/livecfg/{0}"
    StatusAPIURL = "http://api.own3d.tv/rest/live/status.xml?liveid={0}"
    CDN = {
        "cdn1": "rtmp://fml.2010.edgecastcdn.net/202010",
        "cdn2": "rtmp://owned.fc.llnwd.net:1935/owned",
        "cdn3": "http://hwcdn.net/u4k2r7c4/fls",
    }

    @classmethod
    def can_handle_url(self, url):
        return "own3d.tv" in url

    def _get_channel_info(self, url):
        self.logger.debug("Fetching channel info")

        res = urlget(url)
        data = res.text

        liveid = None
        swfurl = None

        match = re.search('flashvars.config = "livecfg/(\d+)', data)
        if match:
            liveid = int(match.group(1))

        match = re.search("document.location.hash='/live/(\d+)'", data)
        if match:
            liveid = int(match.group(1))

        match = re.search("xajax_load_live_config\((\d+),", data)
        if match:
            liveid = int(match.group(1))

        match = re.search("""swfobject.embedSWF\(\n.+"(.+)", "player",""", data)
        if match:
            swfurl = match.group(1)

        return (liveid, swfurl)

    def _is_live(self, liveid):
        res = urlget(self.StatusAPIURL.format(liveid))

        dom = res_xml(res, "status XML")

        live = dom.getElementsByTagName("live_is_live")

        if len(live) > 0:
            return get_node_text(live[0]) == "1"

        return False

    def _get_streams(self):
        (liveid, swfurl) = self._get_channel_info(self.url)

        if not (liveid and swfurl):
            raise NoStreamsError(self.url)

        if not self._is_live(liveid):
            raise NoStreamsError(self.url)

        self.logger.debug("Fetching stream info")
        res = urlget(self.ConfigURL.format(liveid))

        dom = res_xml(res, "config XML")

        streams = {}
        channels = dom.getElementsByTagName("channels")[0]
        clip = channels.getElementsByTagName("clip")[0]
        items = clip.getElementsByTagName("item")

        for item in items:
            base = item.getAttribute("base")
            if not base:
                continue

            if base[0] == "$":
                ref = re.match("\${(.+)}", base).group(1)
                base = self.CDN[ref]

            for streamel in item.getElementsByTagName("stream"):
                name = streamel.getAttribute("label").lower().replace(" ", "_")
                playpath = streamel.getAttribute("name")

                stream = RTMPStream(self.session, {
                    "rtmp": ("{0}/{1}").format(base, playpath),
                    "live": True,
                    "swfVfy": swfurl,
                    "pageUrl": self.url
                })

                if not name in streams:
                    streams[name] = stream
                else:
                    index = items.index(item)

                    if index == 1:
                        streams[name + "_alt"] = stream
                    else:
                        streams[name + "_alt" + str(index)] = stream

        return streams

__plugin__ = OwnedTV
