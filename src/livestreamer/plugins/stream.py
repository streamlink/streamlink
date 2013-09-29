from livestreamer.compat import urlparse
from livestreamer.exceptions import NoStreamsError
from livestreamer.plugin import Plugin
from livestreamer.stream import (AkamaiHDStream, HDSStream, HLSStream,
                                 HTTPStream, RTMPStream)

import ast
import re

class StreamURL(Plugin):
    ProtocolMap = {
        "akamaihd": AkamaiHDStream,
        "hds": HDSStream.parse_manifest,
        "hls": HLSStream,
        "hlsvariant": HLSStream.parse_variant_playlist,
        "httpstream": HTTPStream,
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
                    val = ast.literal_eval(val)
                except:
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

        # Prepend http:// if needed.
        if cls != RTMPStream and not re.match("^http(s)?://", urlnoproto):
            urlnoproto = "http://{0}".format(urlnoproto)

        params = (" ").join(split[1:])
        params = self._parse_params(params)

        if cls == RTMPStream:
            params["rtmp"] = url

            for boolkey in ("live", "realtime", "quiet", "verbose", "debug"):
                if boolkey in params:
                    params[boolkey] = bool(params[boolkey])

            stream = cls(self.session, params)
        elif cls == HLSStream.parse_variant_playlist or cls == HDSStream.parse_manifest:
            return cls(self.session, urlnoproto, **params)
        else:
            stream = cls(self.session, urlnoproto, **params)

        return dict(live=stream)


__plugin__ = StreamURL
