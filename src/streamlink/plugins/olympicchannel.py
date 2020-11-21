import json
import logging
import re
from time import time
from urllib.parse import urljoin, urlparse

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)


class OlympicChannel(Plugin):
    _url_re = re.compile(r"https?://(\w+\.)olympicchannel.com/../(?P<type>live|video|original-series|films)/?(?:\w?|[-\w]+)")
    _tokenizationApiDomainUrl = """"tokenizationApiDomainUrl" content="/OcsTokenization/api/v1/tokenizedUrl">"""
    _live_api_path = "/OcsTokenization/api/v1/tokenizedUrl?url={url}&domain={netloc}&_ts={time}"

    _api_schema = validate.Schema(
        validate.text,
        validate.transform(lambda v: json.loads(v)),
        validate.url()
    )
    _video_url_re = re.compile(r""""video_url"\scontent\s*=\s*"(?P<value>[^"]+)""")
    _video_url_schema = validate.Schema(
        validate.contains(_tokenizationApiDomainUrl),
        validate.transform(_video_url_re.search),
        validate.any(None, validate.get("value")),
        validate.url()
    )

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url)

    def _get_vod_streams(self):
        stream_url = self.session.http.get(self.url, schema=self._video_url_schema)
        return HLSStream.parse_variant_playlist(self.session, stream_url)

    def _get_live_streams(self):
        video_url = self.session.http.get(self.url, schema=self._video_url_schema)
        parsed = urlparse(video_url)
        api_url = urljoin(self.url, self._live_api_path.format(url=video_url,
                          netloc="{0}://{1}".format(parsed.scheme, parsed.netloc), time=int(time())))
        stream_url = self.session.http.get(api_url, schema=self._api_schema)
        return HLSStream.parse_variant_playlist(self.session, stream_url)

    def _get_streams(self):
        match = self._url_re.match(self.url)
        type_of_stream = match.group('type')

        if type_of_stream == 'live':
            return self._get_live_streams()
        elif type_of_stream in ('video', 'original-series', 'films'):
            return self._get_vod_streams()


__plugin__ = OlympicChannel
