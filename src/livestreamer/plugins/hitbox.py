from livestreamer.stream import RTMPStream, HTTPStream
from livestreamer.plugin import Plugin
from livestreamer.exceptions import NoStreamsError
from livestreamer.utils import urlget, verifyjson, res_json

import re

LIVE_API = "http://www.hitbox.tv/api/media/live/{0}?showHidden=true"
PLAYER_API = "http://www.hitbox.tv/api/player/config/{0}/{1}?embed=false&showHidden=true"

# you can get this from http://www.hitbox.tv/js/hitbox-combined.js
# but a 1.4MB download seems a bit much ;)
# lets hope it doesn't change much...
SWF_BASE = "http://edge.vie.hitbox.tv/static/player/flowplayer/"


class Hitbox(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return "hitbox.tv" in url

    def _get_quality(self, label):
        match = re.search(r".*?(\d+p)", label)
        if match:
            return match.group(1)
        return "live"

    def _get_streams(self):
        self.logger.debug("Fetching stream info")
        media_is_live = 0

        match = re.search(r".*hitbox.tv/([^/]*)/?(\d+)?", self.url)
        if not match:
            raise NoStreamsError(self.url)

        stream_name, media_id = match.groups()

        if stream_name != "video":
            res = urlget(LIVE_API.format(stream_name))
            json = res_json(res)
            livestream = verifyjson(json, "livestream")
            media_id = verifyjson(livestream[0], "media_id")
            media_is_live = int(verifyjson(livestream[0], "media_is_live"))
            if not media_is_live:
                raise NoStreamsError(self.url)

        media_type = "live" if media_is_live else "video"
        res = urlget(PLAYER_API.format(media_type, media_id))
        json = res_json(res)
        clip = verifyjson(json, "clip")
        live = verifyjson(clip, "live")
        bitrates = verifyjson(clip, "bitrates")

        streams = {}
        if live:
            for bitrate in bitrates:
                connection_provider = clip.get("connectionProvider", "clustering")
                plugins = verifyjson(json, "plugins")
                provider_plugin = verifyjson(plugins, connection_provider)
                swf = verifyjson(provider_plugin, "url")
                rtmp = verifyjson(provider_plugin, "netConnectionUrl")
                quality = self._get_quality(verifyjson(bitrate, "label"))
                url = verifyjson(bitrate, "url")

                streams[quality] = RTMPStream(self.session, {
                    "rtmp": rtmp,
                    "pageUrl": self.url,
                    "playpath": url,
                    "swfVfy": SWF_BASE + swf,
                    "live": True
                })
        else:
            for bitrate in bitrates:
                base_url = verifyjson(clip, "baseUrl")
                url = verifyjson(bitrate, "url")
                quality = self._get_quality(verifyjson(bitrate, "label"))
                streams[quality] = HTTPStream(self.session,
                                              base_url + "/" + url)

        return streams

__plugin__ = Hitbox
