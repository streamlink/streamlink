from livestreamer.compat import urlparse
from livestreamer.plugin import Plugin
from livestreamer.stream import HLSStream


class OldLivestream(Plugin):
    PlaylistURL = "http://x{0}x.api.channel.livestream.com/3.0/playlist.m3u8"

    @classmethod
    def can_handle_url(self, url):
        return "livestream.com" in url and not "new.livestream.com" in url

    def _get_streams(self):
        channelname = urlparse(self.url).path.rstrip("/").rpartition("/")[-1].lower()
        channelname = channelname.replace("_", "-")

        try:
            streams = HLSStream.parse_variant_playlist(self.session,
                                                       self.PlaylistURL.format(channelname))
        except IOError:
            return

        return streams


__plugin__ = OldLivestream
