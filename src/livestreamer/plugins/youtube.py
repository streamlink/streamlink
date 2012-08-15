from livestreamer.compat import str, bytes, parse_qs
from livestreamer.plugins import Plugin, PluginError, NoStreamsError, register_plugin
from livestreamer.stream import HTTPStream
from livestreamer.utils import urlget, verifyjson

import re
import json

class Youtube(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return "youtube.com" in url

    def _get_stream_info(self, url):
        data = urlget(url)
        config = None

        match = re.search(b"'PLAYER_CONFIG': (.+)\n.+}\);", data)
        if match:
            config = match.group(1)

        match = re.search(b"yt.playerConfig = (.+)\;\n", data)
        if match:
            config = match.group(1)

        if config:
            try:
                parsed = json.loads(str(config, "utf8"))
            except ValueError as err:
                raise PluginError(("Unable to parse config JSON: {0})").format(err))

            return parsed

    def _parse_stream_map(self, streammap):
        streams = []

        for stream_qs in streammap.split(","):
            stream = parse_qs(stream_qs)
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
            if not "url" in streaminfo:
                continue

            stream = HTTPStream(streaminfo["url"][0])

            if streaminfo["itag"][0] in formatmap:
                quality = formatmap[streaminfo["itag"][0]]
            else:
                quality = streaminfo["quality"]

            streams[quality] = stream

        return streams

register_plugin("youtube", Youtube)
