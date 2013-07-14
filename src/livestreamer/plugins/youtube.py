from livestreamer.exceptions import NoStreamsError
from livestreamer.plugin import Plugin
from livestreamer.stream import HTTPStream, HLSStream
from livestreamer.utils import urlget, verifyjson, parse_json, parse_qsd

import re

class Youtube(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return "youtube.com" in url

    def _find_config(self, data):
        match = re.search("'PLAYER_CONFIG': (.+)\n.+}\);", data)
        if match:
            return match.group(1)

        match = re.search("yt.playerConfig = (.+)\;\n", data)
        if match:
            return match.group(1)

        match = re.search("ytplayer.config = (.+);</script>", data)
        if match:
            return match.group(1)

        match = re.search("data-swf-config=\"(.+)\"", data)
        if match:
            config = match.group(1)
            config = config.replace("&amp;quot;", "\"")

            return config

    def _get_stream_info(self, url):
        res = urlget(url)
        config = self._find_config(res.text)

        if config:
            return parse_json(config, "config JSON")

    def _parse_stream_map(self, streammap):
        streams = []

        for stream_qs in streammap.split(","):
            stream = parse_qsd(stream_qs)
            streams.append(stream)

        return streams

    def _parse_format_map(self, formatsmap):
        formats = {}

        if len(formatsmap) == 0:
            return formats

        for format in formatsmap.split(","):
            s = format.split("/")
            (w, h) = s[1].split("x")
            formats[s[0]] = h + "p"

        return formats

    def _get_streams(self):
        info = self._get_stream_info(self.url)

        if not info:
            raise NoStreamsError(self.url)

        args = verifyjson(info, "args")

        if not "live_playback" in args or args["live_playback"] == "0":
            raise NoStreamsError(self.url)

        streams = {}

        uestreammap = verifyjson(args, "url_encoded_fmt_stream_map")
        fmtlist = verifyjson(args, "fmt_list")

        streammap = self._parse_stream_map(uestreammap)
        formatmap = self._parse_format_map(fmtlist)

        for streaminfo in streammap:
            if not ("url" in streaminfo and "sig" in streaminfo):
                continue

            stream = HTTPStream(self.session, streaminfo["url"],
                                params=dict(signature=streaminfo["sig"]))

            if streaminfo["itag"] in formatmap:
                quality = formatmap[streaminfo["itag"]]
            else:
                quality = streaminfo["quality"]

            streams[quality] = stream

        if "hlsvp" in args:
            url = args["hlsvp"]

            try:
                hlsstreams = HLSStream.parse_variant_playlist(self.session, url,
                                                              namekey="pixels")
                streams.update(hlsstreams)
            except IOError as err:
                self.logger.warning("Failed to get variant playlist: {0}", err)

        return streams

__plugin__ = Youtube
