import logging
import re

from streamlink.compat import parse_qsl, urlparse
from streamlink.plugin import Plugin
from streamlink.plugin.api import useragents
from streamlink.plugin.api.utils import itertags
from streamlink.stream import HLSStream, HTTPStream

log = logging.getLogger(__name__)


class LiveRussia(Plugin):
    url_re = re.compile(
        r"https?://(?:live\.)?russia\.tv/(channel/([0-9]+))?")
    _data_re = re.compile(
        r"""window\.pl\.data\.([\w_]+)\s*=\s*['"]?(.*?)['"]?;""")
    channel = ''

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None


    def _get_iframe_url(self, url):
        live = self.url_re.match(self.url)
        channel = live.group(2)
        log.debug("Channel: {0}".format(channel))
        if channel: 
            self.channel = channel
            template = "https://live.russia.tv/api/now/channel/{0}"
            return template.format(channel)
        else:
            res = self.session.http.get(url)
            for iframe in itertags(res.text, 'iframe'):
                src = iframe.attributes.get("src")
                if src:
                    return src


    def _get_stream_info_url(self, url):
        res = self.session.http.get(url)
        data = {}
        if self.channel:
            args = dict(parse_qsl(urlparse(url).query))
            if not args:
                data = self.session.http.json(res)
                args["id"] = data["live_id"]
                args["sid"] = "rutv"
            template = '''
                https://player.vgtrk.com/iframe/datalive/id/{id}/sid/{sid}'''
            stream_info_url = template.format(**args)
        else:
            for m in self._data_re.finditer(res.text):
                data[m.group(1)] = m.group(2)

            if data["isVod"] == '0':
                tamplate = "https:{domain}/iframe/datalive/id/{id}/sid/{sid}"
                stream_info_url = tamplate.format(**data)
            else:
                template = "https:{domain}/iframe/datavideo/id/{id}/sid/{sid}"
                stream_info_url = template.format(**data)

        log.debug("Got pl_data:")
        for key in data:
            log.debug(u'    {0}: {1}'.format(key, data[key]))
        return stream_info_url


    def _get_streams(self):
        self.session.http.headers.update(
            {"User-Agent": useragents.FIREFOX})
        iframe_url = self._get_iframe_url(self.url)

        if iframe_url:
            log.debug("Found iframe URL: {0}".format(iframe_url))
            info_url = self._get_stream_info_url(iframe_url)
            if info_url:
                log.debug('Getting info from URL: {0}'.format(info_url))
                res = self.session.http.get(
                    info_url, headers={"Referer": iframe_url})
                data = self.session.http.json(res)
                if data['status'] == 200:
                    for media in data['data']['playlist']['medialist']:
                        if media['errors']:
                            log.error(media['errors'].replace(
                                '\n', '').replace('\r', ''))

                        for media_type in media.get('sources', []):
                            if media_type == "m3u8":
                                hls_url = media['sources'][media_type]['auto']
                                log.debug("hls_url={0}".format(hls_url))
                                for s in HLSStream.parse_variant_playlist(
                                    self.session, hls_url).items():
                                    yield s

                            if media_type == "http":
                                for pix, http_url in media['sources'][
                                    media_type].items():
                                    log.debug("http_url={0}".format(http_url))
                                    yield "{0}p".format(pix), HTTPStream(
                                        self.session, http_url)
                else:
                    log.error("An error occurred: {0}".format(
                        data['errors'].replace('\n', '').replace('\r', '')))
            else:
                log.error("Unable to get stream info URL")

        else:
            log.error("Unable to get iframe URL")

__plugin__ = LiveRussia
