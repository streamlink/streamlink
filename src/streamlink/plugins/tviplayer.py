import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import useragents, validate
from streamlink.stream.hls import HLSStream

from urllib.parse import urlparse, urlunparse, parse_qs, urlencode


@pluginmatcher(re.compile(  # Live
    r'https://tviplayer.iol.pt/direto/(?P<channel>\w+)'
))
@pluginmatcher(re.compile(  # Episodes
    r'https?://tviplayer.iol.pt/programa/(?P<sname>\S+)/(?P<sid>\w+)/video/(?P<eid>\w+)',
))
class TVIPlayer(Plugin):
    _m3u8_re = re.compile(r'''"videoUrl":\s*"(?P<m3u8>[^"]+)"''')

    _schema_token = validate.Schema(
        validate.all(
            str,
            validate.any(
                validate.length(0),
            ),
        ),
    )
    _schema_hls = validate.Schema(
        validate.transform(lambda text: next(reversed(list(TVIPlayer._m3u8_re.finditer(text))), None)),
        validate.all(
            validate.get('m3u8'),
            str,
            validate.any(
                validate.length(0),
                validate.url()
            ),
        ),
    )

    def _get_streams(self):
        self.session.http.headers.update({
            "User-Agent": useragents.FIREFOX,
            'Referer': 'https://tviplayer.iol.pt/',  # Homepage
        })
        # Get a wmsAuthSign
        wmsAuthSign = self.session.http.get('https://services.iol.pt/matrix?userId=', schema=self._schema_token)

        # Get the HLS
        self.session.http.headers.update({'Referer': self.url})
        hls_url = self.session.http.get(self.url, schema=self._schema_hls)
        if hls_url:
            # - Append the wmsAuthSign
            raw_url = urlparse(hls_url)
            qs = parse_qs(raw_url.query)
            qs['wmsAuthSign'] = wmsAuthSign
            new_hls_url = urlunparse(raw_url._replace(query=urlencode(qs, doseq=True)))
            return HLSStream.parse_variant_playlist(self.session, new_hls_url)


__plugin__ = TVIPlayer
