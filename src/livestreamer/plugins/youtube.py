from livestreamer.exceptions import NoStreamsError
from livestreamer.plugin import Plugin
from livestreamer.stream import HTTPStream, HLSStream
from livestreamer.utils import urlget, verifyjson, parse_json, parse_qsd

import re

class Youtube(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return "youtube.com" in url

    @classmethod
    def stream_weight(cls, stream):
        match = re.match("(\w+)_3d", stream)
        if match:
            weight, group = Plugin.stream_weight(match.group(1))
            weight -= 1
            group = "youtube_3d"
        else:
            weight, group = Plugin.stream_weight(stream)

        return weight, group

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

        streams = {}

        uestreammap = verifyjson(args, "url_encoded_fmt_stream_map")
        fmtlist = verifyjson(args, "fmt_list")

        streammap = self._parse_stream_map(uestreammap)
        formatmap = self._parse_format_map(fmtlist)

        for streaminfo in streammap:
            if "s" in streaminfo and self._decrypt_signature(streaminfo["s"]):
                streaminfo["sig"] = self._decrypt_signature(streaminfo["s"])

            if not ("url" in streaminfo and "sig" in streaminfo):
                continue

            stream = HTTPStream(self.session, streaminfo["url"],
                                params=dict(signature=streaminfo["sig"]))

            if streaminfo["itag"] in formatmap:
                quality = formatmap[streaminfo["itag"]]
            else:
                quality = streaminfo["quality"]

            if streaminfo.get("stereo3d") == "1":
                quality += "_3d"

            streams[quality] = stream

        if "hlsvp" in args:
            url = args["hlsvp"]

            try:
                hlsstreams = HLSStream.parse_variant_playlist(self.session, url,
                                                              namekey="pixels")
                streams.update(hlsstreams)
            except IOError as err:
                self.logger.warning("Failed to get variant playlist: {0}", err)

        if not streams and args.get("live_playback", "0") == "0":
            self.logger.warning("VOD support may not be 100% complete. Try youtube-dl instead.")

        return streams

    def _decrypt_signature(self, s):
        """ 
            Turn the encrypted s field into a working signature
            https://github.com/rg3/youtube-dl/blob/master/youtube_dl/extractor/youtube.py
        """

        if len(s) == 92:
            return s[25] + s[3:25] + s[0] + s[26:42] + s[79] + s[43:79] + s[91] + s[80:83]
        elif len(s) == 90:
            return s[25] + s[3:25] + s[2] + s[26:40] + s[77] + s[41:77] + s[89] + s[78:81]
        elif len(s) == 88:
            return s[48] + s[81:67:-1] + s[82] + s[66:62:-1] + s[85] + s[61:48:-1] + s[67] + s[47:12:-1] + s[3] + s[11:3:-1] + s[2] + s[12]
        elif len(s) == 87:
            return s[4:23] + s[86] + s[24:85]
        elif len(s) == 86:
            return s[83:85] + s[26] + s[79:46:-1] + s[85] + s[45:36:-1] + s[30] + s[35:30:-1] + s[46] + s[29:26:-1] + s[82] + s[25:1:-1]
        elif len(s) == 85:
            return s[2:8] + s[0] + s[9:21] + s[65] + s[22:65] + s[84] + s[66:82] + s[21]
        elif len(s) == 84:
            return s[83:36:-1] + s[2] + s[35:26:-1] + s[3] + s[25:3:-1] + s[26]
        elif len(s) == 83:
            return s[6] + s[3:6] + s[33] + s[7:24] + s[0] + s[25:33] + s[53] + s[34:53] + s[24] + s[54:]
        elif len(s) == 82:
            return s[36] + s[79:67:-1] + s[81] + s[66:40:-1] + s[33] + s[39:36:-1] + s[40] + s[35] + s[0] + s[67] + s[32:0:-1] + s[34]
        elif len(s) == 81:
            return s[56] + s[79:56:-1] + s[41] + s[55:41:-1] + s[80] + s[40:34:-1] + s[0] + s[33:29:-1] + s[34] + s[28:9:-1] + s[29] + s[8:0:-1] + s[9]
        elif len(s) == 79:
            return s[54] + s[77:54:-1] + s[39] + s[53:39:-1] + s[78] + s[38:34:-1] + s[0] + s[33:29:-1] + s[34] + s[28:9:-1] + s[29] + s[8:0:-1] + s[9]
        else:
            self.logger.warning("Unable to decrypt signature, key length {0} not supported; retrying might work", len(s))
            return None

__plugin__ = Youtube
