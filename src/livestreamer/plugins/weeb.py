from livestreamer.exceptions import PluginError, NoStreamsError
from livestreamer.plugin import Plugin
from livestreamer.stream import RTMPStream
from livestreamer.utils import urlget, urlopen, parse_qsd

import re

class Weeb(Plugin):
    SWFURL = "http://static2.weeb.tv/static2/player.swf"
    APIURL = "http://weeb.tv/api/setPlayer"

    @classmethod
    def can_handle_url(self, url):
        return "weeb.tv" in url

    def _get_streams(self):
        self.logger.debug("Fetching stream info")

        headers = {
            "Referer": self.url
        }

        res = urlget(self.url, headers=headers)
        match = re.search("flashvars.*?cid[^\d]+?(\d+)", res.text)
        if not match:
            raise NoStreamsError(self.url)

        headers = {
            "Referer": self.SWFURL
        }

        form = dict(cid=match.group(1), watchTime="0",
                    firstConnect="1", ip="NaN")

        res = urlopen(self.APIURL, data=form, headers=headers)

        params = parse_qsd(res.text)

        if "0" in params and int(params["0"]) <= 0:
            raise PluginError("Server refused to send required parameters.")

        rtmp = params["10"]
        playpath = params["11"]
        multibitrate = int(params["20"])
        premiumuser = params["5"]
        blocktype = int(params["13"])

        if blocktype != 0:
            if blocktype == 1:
                blocktime = params["14"]
                reconnectiontime = params["16"]
                msg = ("You have crossed free viewing limit. ",
                       "You have been blocked for %s minutes. " % blocktime,
                       "Try again in %s minutes." % reconnectiontime)
                raise PluginError(msg)
            elif blocktype == 11:
                raise PluginError("No free slots available.")

        if "73" in params:
            token = params["73"]
        else:
            raise PluginError("Server seems busy, please try after some time.")

        if not RTMPStream.is_usable(self.session):
            raise PluginError("rtmpdump is not usable and required by Weeb plugin")

        streams = {}

        if multibitrate:
            streams["low"] = RTMPStream(self.session, {
                "rtmp": "{0}/{1}".format(rtmp, playpath),
                "pageUrl": self.url,
                "swfVfy": self.SWFURL,
                "weeb": token,
                "live": True
            })
            playpath += "HI"

        streams["live"] = RTMPStream(self.session, {
            "rtmp": "{0}/{1}".format(rtmp, playpath),
            "pageUrl": self.url,
            "swfVfy": self.SWFURL,
            "weeb": token,
            "live": True
        })

        return streams


__plugin__ = Weeb
