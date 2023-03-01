"""
$description Live TV channels and video on-demand service from RTBF, a Belgian public broadcaster.
$url rtbf.be/auvio
$url rtbfradioplayer.be
$type live, vod
$region Belgium, Europe
"""

import datetime
import logging
import re
from html import unescape as html_unescape

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.dash import DASHStream
from streamlink.stream.hls import HLSStream
from streamlink.stream.http import HTTPStream
from streamlink.utils.times import parse_datetime


log = logging.getLogger(__name__)


@pluginmatcher(re.compile(r"""
    https?://(?:www\.)?
    (?:
        rtbf\.be/auvio/.*\?l?id=(?P<video_id>\d+)#?
        |
        rtbfradioplayer\.be/radio/liveradio/.+
    )
""", re.VERBOSE))
class RTBF(Plugin):
    GEO_URL = "https://www.rtbf.be/api/geoloc"
    TOKEN_URL = "https://token.rtbf.be/"
    RADIO_STREAM_URL = "http://www.rtbfradioplayer.be/radio/liveradio/rtbf/radios/{}/config.json"

    _stream_size_re = re.compile(
        r"https?://.+-(?P<size>\d+p?)\..+?$",
    )

    _video_player_re = re.compile(
        r'<iframe\s+class="embed-responsive-item\s+js-embed-iframe".*src="(?P<player_url>.+?)".*?</iframe>',
        re.DOTALL,
    )
    _video_stream_data_re = re.compile(
        r'<div\s+id="js-embed-player"\s+class="js-embed-player\s+embed-player"\s+data-media="(.+?)"',
    )
    _radio_id_re = re.compile(
        r'var currentStationKey = "(?P<radio_id>.+?)"',
    )

    _geo_schema = validate.Schema(
        {
            "country": str,
            "zone": str,
        },
    )

    _video_stream_schema = validate.Schema(
        validate.transform(_video_stream_data_re.search),
        validate.any(
            None,
            validate.all(
                validate.get(1),
                validate.transform(html_unescape),
                validate.parse_json(),
                {
                    "geoLocRestriction": str,
                    validate.optional("isLive"): bool,
                    validate.optional("startDate"): str,
                    validate.optional("endDate"): str,
                    "sources": validate.any(
                        [],
                        validate.Schema({
                            str: validate.any(None, "", validate.url()),
                        }),
                    ),
                    validate.optional("urlHls"): validate.any(None, "", validate.url()),
                    validate.optional("urlDash"): validate.any(None, "", validate.url()),
                    validate.optional("streamUrlHls"): validate.any(None, "", validate.url()),
                    validate.optional("streamUrlDash"): validate.any(None, "", validate.url()),
                    validate.optional("drm"): bool,
                },
            ),
        ),
    )

    _radio_stream_schema = validate.Schema(
        {
            "audioUrls": validate.all(
                [{
                    "url": validate.url(),
                    "mimeType": str,
                }],
            ),
        },
    )

    def check_geolocation(self, geoloc_flag):
        if geoloc_flag == "open":
            return True

        res = self.session.http.get(self.GEO_URL)
        data = self.session.http.json(res, schema=self._geo_schema)
        return data["country"] == geoloc_flag or data["zone"] == geoloc_flag

    def tokenize_stream(self, url):
        res = self.session.http.post(self.TOKEN_URL, data={"streams[url]": url})
        data = self.session.http.json(res)
        return data["streams"]["url"]

    def _get_radio_streams(self):
        res = self.session.http.get(self.url)
        match = self._radio_id_re.search(res.text)
        if match is None:
            return
        radio_id = match.group("radio_id")
        res = self.session.http.get(self.RADIO_STREAM_URL.format(radio_id))
        streams = self.session.http.json(res, schema=self._radio_stream_schema)

        for stream in streams["audioUrls"]:
            match = self._stream_size_re.match(stream["url"])
            if match is not None:
                quality = "{}k".format(match.group("size"))
            else:
                quality = stream["mimetype"]
            yield quality, HTTPStream(self.session, stream["url"])

    def _get_video_streams(self):
        res = self.session.http.get(self.url)
        match = self._video_player_re.search(res.text)
        if match is None:
            return
        player_url = match.group("player_url")
        stream_data = self.session.http.get(player_url, schema=self._video_stream_schema)
        if stream_data is None:
            return

        # Check geolocation to prevent further errors when stream is parsed
        if not self.check_geolocation(stream_data["geoLocRestriction"]):
            log.error("Stream is geo-restricted")
            return

        # Check whether streams are DRM-protected
        if stream_data.get("drm", False):
            log.error("Stream is DRM-protected")
            return

        now = datetime.datetime.now(datetime.timezone.utc)
        try:
            if isinstance(stream_data["sources"], dict):
                urls = []
                for profile, url in stream_data["sources"].items():
                    if not url or url in urls:
                        continue
                    match = self._stream_size_re.match(url)
                    if match is not None:
                        quality = match.group("size")
                    else:
                        quality = profile
                    yield quality, HTTPStream(self.session, url)
                    urls.append(url)

            hls_url = stream_data.get("urlHls") or stream_data.get("streamUrlHls")
            if hls_url:
                if stream_data.get("isLive", False):
                    # Live streams require a token
                    hls_url = self.tokenize_stream(hls_url)
                yield from HLSStream.parse_variant_playlist(self.session, hls_url).items()

            dash_url = stream_data.get("urlDash") or stream_data.get("streamUrlDash")
            if dash_url:
                if stream_data.get("isLive", False):
                    # Live streams require a token
                    dash_url = self.tokenize_stream(dash_url)
                yield from DASHStream.parse_manifest(self.session, dash_url).items()

        except OSError as err:
            if "403 Client Error" in str(err):
                # Check whether video is expired
                if "startDate" in stream_data:
                    if now < parse_datetime(stream_data["startDate"]):
                        log.error("Stream is not yet available")
                elif "endDate" in stream_data:
                    if now > parse_datetime(stream_data["endDate"]):
                        log.error("Stream has expired")

    def _get_streams(self):
        if self.match.group("video_id"):
            return self._get_video_streams()
        return self._get_radio_streams()


__plugin__ = RTBF
