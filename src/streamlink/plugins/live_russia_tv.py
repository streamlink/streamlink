import logging
import re

from streamlink.compat import parse_qsl, urlparse
from streamlink.plugin import Plugin
from streamlink.plugin.api import useragents
from streamlink.plugin.api.utils import itertags
from streamlink.stream import HLSStream, HTTPStream

log = logging.getLogger(__name__)


class LiveRussia(Plugin):
    url_re = re.compile(r"https?://(?:www\.|live\.)?russia.tv")
    _data_re = re.compile(r"""window\.pl\.data\.([\w_]+)\s*=\s*['"]?(.*?)['"]?;""")

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_iframe_url(self, url):
        res = self.session.http.get(url)
        for iframe in itertags(res.text, 'iframe'):
            src = iframe.attributes.get("src")
            if src:
                return src

    def _get_stream_info_url(self, url):
        data = {}
        res = self.session.http.get(url)
        for m in self._data_re.finditer(res.text):
            data[m.group(1)] = m.group(2)

        log.debug("Got pl_data={0}".format(data))

        if data:
            if data["isVod"] == '0':
                return "https:{domain}/iframe/datalive/id/{id}/sid/{sid}".format(**data)
            else:
                return "https:{domain}/iframe/datavideo/id/{id}/sid/{sid}".format(**data)
        else:
            args = dict(parse_qsl(urlparse(url).query))
            return "https://player.vgtrk.com/iframe/datalive/id/{id}/sid/{sid}".format(**args)

    def _get_streams(self):
        self.session.http.headers.update({"User-Agent": useragents.FIREFOX})
        iframe_url = self._get_iframe_url(self.url)

        if iframe_url:
            log.debug("Found iframe URL={0}".format(iframe_url))
            info_url = self._get_stream_info_url(iframe_url)

            if info_url:
                log.debug("Getting info from URL: {0}".format(info_url))
                res = self.session.http.get(info_url, headers={"Referer": iframe_url})
                data = self.session.http.json(res)

                if data['status'] == 200:
                    for media in data['data']['playlist']['medialist']:
                        if media['errors']:
                            log.error(media['errors'].replace('\n', '').replace('\r', ''))

                        for media_type in media.get('sources', []):

                            if media_type == "m3u8":
                                hls_url = media['sources'][media_type]['auto']
                                for s in HLSStream.parse_variant_playlist(self.session, hls_url).items():
                                    yield s

                            if media_type == "http":
                                for pix, url in media['sources'][media_type].items():
                                    yield "{0}p".format(pix), HTTPStream(self.session, url)
                else:
                    log.error("An error occurred: {0}".format(data['errors'].replace('\n', '').replace('\r', '')))
            else:
                log.error("Unable to get stream info URL")
        else:
            log.error("Could not find video iframe")


__plugin__ = LiveRussia
