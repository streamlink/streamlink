"""Plugin for NPO: Nederlandse Publieke Omroep

Supports:
   VODs:
    - https://www.npo.nl/nos-journaal/07-07-2017/POW_03375651
    - https://www.zapp.nl/topdoks/gemist/VPWON_1276930
    - https://zappelin.nl/10-voor/gemist/VPWON_1271522
   Live:
    - https://www.npo.nl/live/npo-1
    - https://zappelin.nl/tv-kijken
"""

import re

from streamlink.plugin import Plugin, PluginArguments, PluginArgument
from streamlink.plugin.api import http
from streamlink.plugin.api import useragents
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream
from streamlink.stream import HTTPStream
from streamlink.utils import parse_json


class NPO(Plugin):
    api_url = "http://ida.omroep.nl/app.php/{endpoint}"
    url_re = re.compile(r"https?://(\w+\.)?(npo\.nl|zapp\.nl|zappelin\.nl)/")
    media_id_re = re.compile(r'''<npo-player\smedia-id=["'](?P<media_id>[^"']+)["']''')
    prid_re = re.compile(r'''(?:data(-alt)?-)?prid\s*[=:]\s*(?P<q>["'])(\w+)(?P=q)''')
    react_re = re.compile(r'''data-react-props\s*=\s*(?P<q>["'])(?P<data>.*?)(?P=q)''')

    auth_schema = validate.Schema({"token": validate.text}, validate.get("token"))
    streams_schema = validate.Schema({
        "items": [
            [{
                "label": validate.text,
                "contentType": validate.text,
                "url": validate.url(),
                "format": validate.text
            }]
        ]
    }, validate.get("items"), validate.get(0))
    stream_info_schema = validate.Schema(validate.any(
        validate.url(),
        validate.all({"errorcode": 0, "url": validate.url()},
                     validate.get("url"))
    ))
    arguments = PluginArguments(
        PluginArgument(
            "subtitles",
            action="store_true",
            help="""
        Include subtitles for the deaf or hard of hearing, if available.
        """
        )
    )

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def __init__(self, url):
        super(NPO, self).__init__(url)
        self._token = None
        http.headers.update({"User-Agent": useragents.CHROME})

    def api_call(self, endpoint, schema=None, params=None):
        url = self.api_url.format(endpoint=endpoint)
        res = http.get(url, params=params)
        return http.json(res, schema=schema)

    @property
    def token(self):
        if not self._token:
            self._token = self.api_call("auth", schema=self.auth_schema)
        return self._token

    def _get_prid(self, subtitles=False):
        res = http.get(self.url)
        bprid = None

        # Locate the asset id for the content on the page
        for alt, _, prid in self.prid_re.findall(res.text):
            if alt and subtitles:
                bprid = prid
            elif bprid is None:
                bprid = prid

        if bprid is None:
            m = self.react_re.search(res.text)
            if m:
                data = parse_json(m.group("data").replace("&quot;", '"'))
                bprid = data.get("mid")

        if bprid is None:
            m = self.media_id_re.search(res.text)
            if m:
                bprid = m.group('media_id')

        return bprid

    def _get_streams(self):
        asset_id = self._get_prid(self.get_option("subtitles"))

        if asset_id:
            self.logger.debug("Found asset id: {0}", asset_id)
            streams = self.api_call(asset_id,
                                    params=dict(adaptive="yes",
                                                token=self.token),
                                    schema=self.streams_schema)

            for stream in streams:
                if stream["format"] in ("adaptive", "hls", "mp4"):
                    if stream["contentType"] == "url":
                        stream_url = stream["url"]
                    else:
                        # using type=json removes the javascript function wrapper
                        info_url = stream["url"].replace("type=jsonp", "type=json")

                        # find the actual stream URL
                        stream_url = http.json(http.get(info_url),
                                               schema=self.stream_info_schema)

                    if stream["format"] in ("adaptive", "hls"):
                        for s in HLSStream.parse_variant_playlist(self.session, stream_url).items():
                            yield s
                    elif stream["format"] in ("mp3", "mp4"):
                        yield "vod", HTTPStream(self.session, stream_url)


__plugin__ = NPO
