import random
import re

from streamlink.compat import urlencode, unquote, urljoin
from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.plugin.plugin import stream_weight
from streamlink.stream import HLSStream, HTTPStream, DASHStream
from streamlink.utils import update_scheme


class OneTV(Plugin):
    _url_re = re.compile(r"https?://(?:www\.)?(?P<channel>1tv|ctc|chetv|ctclove|domashny).(?:com|ru)/(?P<live>live|online)?")
    _vod_re = re.compile(r"""/video_materials\.json[^'"]*""")
    _vod_id_re = re.compile(r'''data-video-material-id="(\d+)"''')

    _1tv_api = "//stream.1tv.ru/api/playlist/1tvch_as_array.json"
    _ctc_api = "//media.1tv.ru/api/v1/ctc/playlist/{channel}_as_array.json"
    _session_api = "//stream.1tv.ru/get_hls_session"
    _channel_remap = {"chetv": "ctc-che",
                      "ctclove": "ctc-love",
                      "domashny": "ctc-dom"}

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    @classmethod
    def stream_weight(cls, stream):
        return dict(ld=(140, "pixels"), sd=(360, "pixels"), hd=(720, "pixels")).get(stream, stream_weight(stream))

    @property
    def channel(self):
        match = self._url_re.match(self.url)
        c = match and match.group("channel")
        return self._channel_remap.get(c, c)

    @property
    def live_api_url(self):
        channel = self.channel
        if channel == "1tv":
            url = self._1tv_api
        else:
            url = self._ctc_api.format(channel=channel)

        return update_scheme(self.url, url)

    def hls_session(self):
        res = http.get(update_scheme(self.url, self._session_api))
        data = http.json(res)
        # the values are already quoted, we don't want them quoted
        return dict((k, unquote(v)) for k, v in data.items())

    @property
    def is_live(self):
        m = self._url_re.match(self.url)
        return m and m.group("live") is not None

    def vod_data(self, vid=None):
        """
        Get the VOD data path and the default VOD ID
        :return:
        """
        page = http.get(self.url)
        m = self._vod_re.search(page.text)
        vod_data_url = m and urljoin(self.url, m.group(0))
        if vod_data_url:
            self.logger.debug("Found VOD data url: {0}", vod_data_url)
            res = http.get(vod_data_url)
            return http.json(res)

    def _get_streams(self):
        if self.is_live:
            self.logger.debug("Loading live stream for {0}...", self.channel)

            res = http.get(self.live_api_url, data={"r": random.randint(1, 100000)})
            live_data = http.json(res)

            # all the streams are equal for each type, so pick a random one
            hls_streams = live_data.get("hls")
            if hls_streams:
                url = random.choice(hls_streams)
                url = url + '&' + urlencode(self.hls_session())  # TODO: use update_qsd
                for s in HLSStream.parse_variant_playlist(self.session, url, name_fmt="{pixels}_{bitrate}").items():
                    yield s

            mpd_streams = live_data.get("mpd")
            if mpd_streams:
                url = random.choice(mpd_streams)
                for s in DASHStream.parse_manifest(self.session, url).items():
                    yield s

        elif self.channel == "1tv":
            self.logger.debug("Attempting to find VOD stream...", self.channel)
            vod_data = self.vod_data()
            if vod_data:
                self.logger.info(u"Found VOD: {0}".format(vod_data[0]['title']))
                for stream in vod_data[0]['mbr']:
                    yield stream['name'], HTTPStream(self.session, update_scheme(self.url, stream['src']))


__plugin__ = OneTV
