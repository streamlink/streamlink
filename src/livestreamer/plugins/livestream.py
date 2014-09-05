import re

from livestreamer.compat import urljoin
from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http, validate
from livestreamer.plugin.api.utils import parse_json
from livestreamer.stream import AkamaiHDStream, HLSStream

_url_re = re.compile("http(s)?://new.livestream.com/")
_stream_config_schema = validate.Schema({
    "event": {
        "stream_info": validate.any({
            "is_live": bool,
            "qualities": [{
                "bitrate": int,
                "height": int
            }],
            validate.optional("play_url"): validate.url(scheme="http"),
            validate.optional("m3u8_url"): validate.url(
                scheme="http",
                path=validate.endswith(".m3u8")
            ),
        }, None)
    },
    validate.optional("viewerPlusSwfUrl"): validate.url(scheme="http"),
    validate.optional("hdPlayerSwfUrl"): validate.text
})
_smil_schema = validate.Schema(validate.union({
    "http_base": validate.all(
        validate.xml_find("{http://www.w3.org/2001/SMIL20/Language}head/"
                          "{http://www.w3.org/2001/SMIL20/Language}meta"
                          "[@name='httpBase']"),
        validate.xml_element(attrib={
            "content": validate.text
        }),
        validate.get("content")
    ),
    "videos": validate.all(
        validate.xml_findall("{http://www.w3.org/2001/SMIL20/Language}body/"
                             "{http://www.w3.org/2001/SMIL20/Language}switch/"
                             "{http://www.w3.org/2001/SMIL20/Language}video"),
        [
            validate.all(
                validate.xml_element(attrib={
                    "src": validate.text,
                    "system-bitrate": validate.all(
                        validate.text,
                        validate.transform(int)
                    )
                }),
                validate.transform(
                    lambda e: (e.attrib["src"], e.attrib["system-bitrate"])
                )
            )
        ],
    )
}))


class Livestream(Plugin):
    @classmethod
    def default_stream_types(cls, streams):
        return ["akamaihd", "hls"]

    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    def _get_stream_info(self):
        res = http.get(self.url)
        match = re.search("window.config = ({.+})", res.text)
        if match:
            config = match.group(1)
            return parse_json(config, "config JSON",
                              schema=_stream_config_schema)

    def _parse_smil(self, url, swf_url):
        res = http.get(url)
        smil = http.xml(res, "SMIL config", schema=_smil_schema)

        for src, bitrate in smil["videos"]:
            url = urljoin(smil["http_base"], src)
            yield bitrate, AkamaiHDStream(self.session, url, swf=swf_url)

    def _get_streams(self):
        info = self._get_stream_info()
        if not info:
            return

        stream_info = info["event"]["stream_info"]
        if not (stream_info and stream_info["is_live"]):
            # Stream is not live
            return

        play_url = stream_info.get("play_url")
        if play_url:
            swf_url = info.get("viewerPlusSwfUrl") or info.get("hdPlayerSwfUrl")
            if not swf_url.startswith("http"):
                swf_url = "http://" + swf_url

            qualities = stream_info["qualities"]
            for bitrate, stream in self._parse_smil(play_url, swf_url):
                name = "{0}k".format(bitrate / 1000)
                for quality in qualities:
                    if quality["bitrate"] == bitrate:
                        name = "{0}p".format(quality["height"])

                yield name, stream

        m3u8_url = stream_info.get("m3u8_url")
        if m3u8_url:
            streams = HLSStream.parse_variant_playlist(self.session, m3u8_url,
                                                       namekey="pixels")
            # TODO: Replace with "yield from" when dropping Python 2.
            for stream in streams.items():
                yield stream

__plugin__ = Livestream
