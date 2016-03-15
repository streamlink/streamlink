import re

from livestreamer.plugin import Plugin
from livestreamer.stream import HLSStream
from livestreamer.plugin.api import http


_stream_url_re = re.compile(r"http(s)?://(www\.)?mediaklikk.hu/([A-Za-z0-9\-]+)/.*")
_video_url_re = re.compile(r"http(s)?://(www\.)?mediaklikk.hu/video/([A-Za-z0-9\-]+)/.*")
_id_re = re.compile(r'.*data\-streamid="([a-z0-9]+)".*')
_token_re = re.compile(r'.*data\-token="([A-Za-z0-9%]+)".*')
_smil_re = re.compile(r'.*<MediaSource>(?P<smil_url>.*)</MediaSource>.*')

_stream_player_url = "http://player.mediaklikk.hu/player/player-inside-full2.php?streamid={0}&noflash=yes&userid=mtva"
_video_player_url = "http://player.mediaklikk.hu/player/player-external-vod-full.php?token={0}&noflash=yes"


class Mediaklikk(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _stream_url_re.match(url)

    @classmethod
    def stream_weight(cls, key):
        try:
            return int(key), "mediaklikk"
        except:
            return Plugin.stream_weight(key)

    def _get_smil_url(self, regex, player_url):
        # get the id/token
        content = http.get(self.url)
        match = regex.match(content.text.replace("\n", ""))
        if not match:
            return

        # get the url Manifest
        # note: there is load balancing here, we get a different url each
        #       time (thats why we can't simply query by the stream id later)
        content = http.get(player_url.format(match.group(1)))
        match = _smil_re.match(content.text.replace("\n", ""))
        if not match:
            return

        return match.group("smil_url")

    def _get_hls_streams(self):
        smil_url = self._get_smil_url(_id_re, _stream_player_url)
        if not smil_url:
            return

        res = http.get(smil_url)
        xml = http.xml(res)
        quality_levels = xml.find('StreamIndex[@Type="video"]').findall("QualityLevel")

        stream_url = smil_url[:smil_url.find("Manifest")] + "/chunklist_b{0}.m3u8"
        streams = {}
        for level in quality_levels:
            bitrate = level.get("Bitrate")
            max_height = level.get("MaxHeight")
            streams[max_height] = HLSStream(self.session, stream_url.format(bitrate))

        return streams

    def _get_variant_playlist_streams(self):
        smil_url = self._get_smil_url(_token_re, _video_player_url)
        if not smil_url:
            return

        stream_url = smil_url[:smil_url.find("Manifest")] + "/chunklist.m3u8"
        return HLSStream.parse_variant_playlist(self.session, stream_url)

    def _get_streams(self):
        if _video_url_re.match(self.url):
            return self._get_variant_playlist_streams()
        else:
            return self._get_hls_streams()


__plugin__ = Mediaklikk
