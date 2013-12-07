from livestreamer.compat import urlparse
from livestreamer.exceptions import PluginError
from livestreamer.plugin import Plugin
from livestreamer.stream import (AkamaiHDStream, HDSStream, HLSStream,
                                 HTTPStream, RTMPStream)

import ast
import re

PROTOCOL_MAP = {
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
PARAMS_REGEX = r"(\w+)=({.+?}|\[.+?\]|\(.+?\)|'(?:[^'\\]|\\')*'|\"(?:[^\"\\]|\\\")*\"|\S+)"

class StreamURL(Plugin):
    @classmethod
    def can_handle_url(self, url):
        parsed = urlparse(url)

        return parsed.scheme in PROTOCOL_MAP

    def _parse_params(self, params):
        rval = {}
        matches = re.findall(PARAMS_REGEX, params)

        for key, value in matches:
            try:
                value = ast.literal_eval(value)
            except Exception:
                pass

            rval[key] = value

        return rval

    def _get_streams(self):
        parsed = urlparse(self.url)
        cls = PROTOCOL_MAP.get(parsed.scheme)

        if not cls:
            return

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
            try:
                streams = cls(self.session, urlnoproto, **params)
            except IOError as err:
                raise PluginError(err)

            return streams
        else:
            stream = cls(self.session, urlnoproto, **params)

        return dict(live=stream)


__plugin__ = StreamURL
