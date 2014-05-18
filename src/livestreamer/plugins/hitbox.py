import re

from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http
from livestreamer.stream import RTMPStream, HTTPStream
from livestreamer.utils import verifyjson

LIVE_API = "http://www.hitbox.tv/api/media/live/{0}?showHidden=true"
PLAYER_API = "http://www.hitbox.tv/api/player/config/{0}/{1}?embed=false&showHidden=true"
SWF_URL = "http://edge.vie.hitbox.tv/static/player/flowplayer/flowplayer.commercial-3.2.16.swf"


def valid_playlist(playlist):
    return (isinstance(playlist, dict) and "bitrates" in playlist
            and "netConnectionUrl" in playlist)


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
            return

        stream_name, media_id = match.groups()
        if stream_name != "video":
            res = http.get(LIVE_API.format(stream_name))
            json = http.json(res)
            livestream = verifyjson(json, "livestream")
            media_id = verifyjson(livestream[0], "media_id")
            media_is_live = int(verifyjson(livestream[0], "media_is_live"))
            if not media_is_live:
                return

        media_type = "live" if media_is_live else "video"
        res = http.get(PLAYER_API.format(media_type, media_id))
        json = http.json(res)
        clip = verifyjson(json, "clip")
        live = verifyjson(clip, "live")

        streams = {}
        if live:
            playlists = verifyjson(json, "playlist") or []
            for playlist in filter(valid_playlist, playlists):
                bitrates = playlist.get("bitrates")
                rtmp = playlist.get("netConnectionUrl")
                for bitrate in bitrates:
                    quality = self._get_quality(verifyjson(bitrate, "label"))
                    url = verifyjson(bitrate, "url")
                    streams[quality] = RTMPStream(self.session, {
                        "rtmp": rtmp,
                        "pageUrl": self.url,
                        "playpath": url,
                        "swfVfy": SWF_URL,
                        "live": True
                    })
        else:
            bitrates = verifyjson(clip, "bitrates")
            for bitrate in bitrates:
                base_url = verifyjson(clip, "baseUrl")
                url = verifyjson(bitrate, "url")
                quality = self._get_quality(verifyjson(bitrate, "label"))
                streams[quality] = HTTPStream(self.session,
                                              base_url + "/" + url)

        return streams

__plugin__ = Hitbox
