from livestreamer.compat import urlparse
from livestreamer.plugins import Plugin, PluginError, NoStreamsError
from livestreamer.stream import *

import re

class StreamURL(Plugin):
    ProtocolMap = {
        "akamaihd": AkamaiHDStream,
        "hls": HLSStream,
        "hlsvariant": HLSStream.parse_variant_playlist,
        "rtmp": RTMPStream,
        "rtmpe": RTMPStream,
        "rtmps": RTMPStream,
        "rtmpt": RTMPStream,
        "rtmpte": RTMPStream
    }

    @classmethod
    def can_handle_url(self, url):
        parsed = urlparse(url)

        return parsed.scheme in self.ProtocolMap

    def _parse_params(self, params):
        rval = {}

        matches = re.findall("(\w+)=(\d+|\d+.\d+|'(.+)'|\"(.+)\"|\S+)", params)

        for key, val, strval, ex in matches:
            if len(strval) > 0:
                rval[key] = strval
            else:
                try:
                    val = float(val)
                except ValueError:
                    pass

                try:
                    val = int(val)
                except ValueError:
                    pass

                rval[key] = val

        return rval

    def _get_streams(self):
        parsed = urlparse(self.url)

        if not parsed.scheme in self.ProtocolMap:
            raise NoStreamsError(self.url)

        cls = self.ProtocolMap[parsed.scheme]
        split = self.url.split(" ")

        url = split[0]
        urlnoproto = re.match("^\w+://(.+)", url).group(1)

        params = (" ").join(split[1:])
        params = self._parse_params(params)

        if cls == RTMPStream:
            params["rtmp"] = url

            for boolkey in ("live", "realtime", "quiet", "verbose", "debug"):
                if boolkey in params:
                    params[boolkey] = bool(params[boolkey])

            stream = cls(self.session, params)
        elif cls == HLSStream.parse_variant_playlist:
            return cls(self.session, urlnoproto, **params)
        else:
            stream = cls(self.session, urlnoproto, **params)

        return dict(live=stream)


__plugin__ = StreamURL
