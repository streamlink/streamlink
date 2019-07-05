import logging
import re

from streamlink.compat import urlparse
from streamlink.plugin import Plugin
from streamlink.plugin.api import useragents
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream
from streamlink.utils import update_scheme

log = logging.getLogger(__name__)


class CDNBG(Plugin):
    url_re = re.compile(r"""
        https?://(?:www\.)?(?:
            tv\.bnt\.bg/\w+(?:/\w+)?|
            bitelevision\.com/live|
            nova\.bg/live|
            kanal3\.bg/live|
            bgonair\.bg/tvonline|
            inlife\.bg|
            mmtvmusic\.com/live|
            mu-vi\.tv/LiveStreams/pages/Live\.aspx|
            videochanel\.bstv\.bg|
            live\.bstv\.bg|
            bloombergtv.bg/video
        )/?
    """, re.VERBOSE)
    iframe_re = re.compile(r"iframe .*?src=\"((?:https?(?::|&#58;))?//(?:\w+\.)?cdn.bg/live[^\"]+)\"", re.DOTALL)
    sdata_re = re.compile(r"sdata\.src.*?=.*?(?P<q>[\"'])(?P<url>http.*?)(?P=q)")
    hls_file_re = re.compile(r"(src|file): (?P<q>[\"'])(?P<url>(https?:)?//.+?m3u8.*?)(?P=q)")
    hls_src_re = re.compile(r"video src=(?P<url>http[^ ]+m3u8[^ ]*)")

    stream_schema = validate.Schema(
        validate.any(
            validate.all(validate.transform(sdata_re.search), validate.get("url")),
            validate.all(validate.transform(hls_file_re.search), validate.get("url")),
            validate.all(validate.transform(hls_src_re.search), validate.get("url")),
        )
    )

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def find_iframe(self, res):
        p = urlparse(self.url)
        for url in self.iframe_re.findall(res.text):
            if "googletagmanager" not in url:
                url = url.replace("&#58;", ":")
                if url.startswith("//"):
                    return "{0}:{1}".format(p.scheme, url)
                else:
                    return url

    def _get_streams(self):
        self.session.http.headers.update({"User-Agent": useragents.CHROME})
        res = self.session.http.get(self.url)
        iframe_url = self.find_iframe(res)

        if iframe_url:
            log.debug("Found iframe: {0}", iframe_url)
            res = self.session.http.get(iframe_url, headers={"Referer": self.url})
            stream_url = update_scheme(self.url, self.stream_schema.validate(res.text))
            log.warning("SSL Verification disabled.")
            return HLSStream.parse_variant_playlist(self.session,
                                                    stream_url,
                                                    verify=False)


__plugin__ = CDNBG
