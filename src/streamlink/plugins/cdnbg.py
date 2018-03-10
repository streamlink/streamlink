from __future__ import print_function

import re

from streamlink.compat import urlparse
from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.plugin.api import useragents
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream
from streamlink.utils import update_scheme


class CDNBG(Plugin):
    url_re = re.compile(r"""
        https?://(?:www\.)?(?:
            tv\.bnt\.bg/\w+(?:/\w+)?|
            bitelevision\.com/live|
            nova\.bg/live|
            kanal3\.bg/live|
            bgonair\.bg/tvonline|
            tvevropa\.com/na-zhivo|
            bloombergtv.bg/video
        )/?
    """, re.VERBOSE)
    iframe_re = re.compile(r"iframe .*?src=\"((?:https?:)?//(?:\w+\.)?cdn.bg/live[^\"]+)\"", re.DOTALL)
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
                if url.startswith("//"):
                    return "{0}:{1}".format(p.scheme, url)
                else:
                    return url

    def _get_streams(self):
        http.headers = {"User-Agent": useragents.CHROME}
        res = http.get(self.url)
        iframe_url = self.find_iframe(res)

        if iframe_url:
            self.logger.debug("Found iframe: {0}", iframe_url)
            res = http.get(iframe_url, headers={"Referer": self.url})
            stream_url = update_scheme(self.url, self.stream_schema.validate(res.text))
            return HLSStream.parse_variant_playlist(self.session,
                                                    stream_url,
                                                    headers={"User-Agent": useragents.CHROME})


__plugin__ = CDNBG
