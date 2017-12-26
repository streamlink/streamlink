import re

from streamlink import NoStreamsError
from streamlink.exceptions import PluginError
from streamlink.plugin import Plugin
from streamlink.plugin.api import StreamMapper, http, validate
from streamlink.stream import HDSStream, HLSStream, RTMPStream
from streamlink.utils import rtmpparse

STREAM_API_URL = "https://playapi.mtgx.tv/v3/videos/stream/{0}"

_swf_url_re = re.compile(r"data-flashplayer-url=\"([^\"]+)\"")
_player_data_re = re.compile(r"window.fluxData\s*=\s*JSON.parse\(\"(.+)\"\);")

_stream_schema = validate.Schema(
    validate.any(
        None,
        validate.all({"msg": validate.text}),
        validate.all({
            "streams": validate.all(
                {validate.text: validate.any(validate.text, int, None)},
                validate.filter(lambda k, v: isinstance(v, validate.text))
            )
        }, validate.get("streams"))
    )
)


class Viasat(Plugin):
    """Streamlink Plugin for Viasat"""

    _iframe_re = re.compile(r"""<iframe.+src=["'](?P<url>[^"']+)["'].+allowfullscreen""")
    _image_re = re.compile(r"""<meta\sproperty=["']og:image["']\scontent=".+/(?P<stream_id>\d+)/[^/]+\.jpg""")

    _url_re = re.compile(r"""https?://(?:www\.)?
        (?:
            juicyplay\.dk
            |
            play\.nova\.bg
            |
            (?:tvplay\.)?
                skaties\.lv
            |
            (?:(?:tv3)?play\.)?
                tv3\.(?:dk|ee|lt)
            |
            tv6play\.no
            |
            viafree\.(?:dk|no|se)
        )
        /(?:
            (?:
                .+/
            |
                embed\?id=
            )
            (?P<stream_id>\d+)
        )?
    """, re.VERBOSE)

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url)

    def _get_swf_url(self):
        res = http.get(self.url)
        match = _swf_url_re.search(res.text)
        if not match:
            raise PluginError("Unable to find SWF URL in the HTML")

        return match.group(1)

    def _create_dynamic_streams(self, stream_type, parser, video):
        try:
            streams = parser(self.session, video[1])
            return streams.items()
        except IOError as err:
            self.logger.error("Failed to extract {0} streams: {1}", stream_type, err)

    def _create_rtmp_stream(self, video):
        name, stream_url = video
        params = {
            "rtmp": stream_url,
            "pageUrl": self.url,
            "swfVfy": self._get_swf_url(),
        }

        if stream_url.endswith(".mp4"):
            tcurl, playpath = rtmpparse(stream_url)
            params["rtmp"] = tcurl
            params["playpath"] = playpath
        else:
            params["live"] = True

        return name, RTMPStream(self.session, params)

    def _extract_streams(self, stream_id):
        res = http.get(STREAM_API_URL.format(stream_id), raise_for_status=False)
        stream_info = http.json(res, schema=_stream_schema)

        if stream_info.get("msg"):
            # error message
            self.logger.error(stream_info.get("msg"))
            raise NoStreamsError(self.url)

        mapper = StreamMapper(lambda pattern, video: re.search(pattern, video[1]))
        mapper.map(
            r"/\w+\.m3u8",
            self._create_dynamic_streams,
            "HLS", HLSStream.parse_variant_playlist
        )
        mapper.map(
            r"/\w+\.f4m",
            self._create_dynamic_streams,
            "HDS", HDSStream.parse_manifest
        )
        mapper.map(r"^rtmp://", self._create_rtmp_stream)

        return mapper(stream_info.items())

    def _get_stream_id(self, text):
        """Try to find a stream_id"""
        m = self._image_re.search(text)
        if m:
            return m.group("stream_id")

    def _get_iframe(self, text):
        """Fallback if no stream_id was found before"""
        m = self._iframe_re.search(text)
        if m:
            return self.session.streams(m.group("url"))

    def _get_streams(self):
        match = self._url_re.match(self.url)
        stream_id = match.group("stream_id")

        if not stream_id:
            text = http.get(self.url).text
            stream_id = self._get_stream_id(text)

            if not stream_id:
                return self._get_iframe(text)

        if stream_id:
            return self._extract_streams(stream_id)


__plugin__ = Viasat
