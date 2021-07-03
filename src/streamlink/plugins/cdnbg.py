import logging
import re
from html import unescape as html_unescape
from urllib.parse import urlparse

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.plugin.api.utils import itertags
from streamlink.stream import HLSStream
from streamlink.utils import update_scheme

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(r"""
    https?://(?:www\.)?(?:
        armymedia\.bg|
        bgonair\.bg/tvonline|
        bloombergtv\.bg/video|
        (?:tv\.)?bnt\.bg/\w+(?:/\w+)?|
        live\.bstv\.bg|
        i\.cdn\.bg/live/|
        nova\.bg/live|
        mu-vi\.tv/LiveStreams/pages/Live\.aspx
    )/?
""", re.VERBOSE))
class CDNBG(Plugin):
    _re_frame = re.compile(r"'src',\s*'(https?://i\.cdn\.bg/live/\w+)'\);")
    sdata_re = re.compile(r"sdata\.src.*?=.*?(?P<q>[\"'])(?P<url>http.*?)(?P=q)")
    hls_file_re = re.compile(r"(src|file): (?P<q>[\"'])(?P<url>(https?:)?//.+?m3u8.*?)(?P=q)")
    hls_src_re = re.compile(r"video src=(?P<url>http[^ ]+m3u8[^ ]*)")
    _re_source_src = re.compile(r"source src=\"(?P<url>[^\"]+m3u8[^\"]*)\"")
    _re_geoblocked = re.compile(r"(?P<url>[^\"]+geoblock[^\"]+)")

    stream_schema = validate.Schema(
        validate.any(
            validate.all(validate.transform(sdata_re.search), validate.get("url")),
            validate.all(validate.transform(hls_file_re.search), validate.get("url")),
            validate.all(validate.transform(hls_src_re.search), validate.get("url")),
            validate.all(validate.transform(_re_source_src.search), validate.get("url")),
            # GEOBLOCKED
            validate.all(validate.transform(_re_geoblocked.search), validate.get("url")),
        )
    )

    def _get_streams(self):
        if "cdn.bg" in urlparse(self.url).netloc:
            iframe_url = self.url
            h = self.session.get_option("http-headers")
            if h and h.get("Referer"):
                _referer = h.get("Referer")
            else:
                log.error("Missing Referer for iframe URL, use --http-header \"Referer=URL\" ")
                return
        else:
            _referer = self.url
            res = self.session.http.get(self.url)
            m = self._re_frame.search(res.text)
            if m:
                iframe_url = m.group(1)
            else:
                for iframe in itertags(res.text, "iframe"):
                    iframe_url = iframe.attributes.get("src")
                    if iframe_url and "cdn.bg" in iframe_url:
                        iframe_url = update_scheme(self.url, html_unescape(iframe_url))
                        break
                else:
                    return
        log.debug(f"Found iframe: {iframe_url}")

        res = self.session.http.get(iframe_url, headers={"Referer": _referer})
        stream_url = self.stream_schema.validate(res.text)
        if "geoblock" in stream_url:
            log.error("Geo-restricted content")
            return

        return HLSStream.parse_variant_playlist(
            self.session,
            update_scheme(iframe_url, stream_url),
            headers={"Referer": "https://i.cdn.bg/"},
        )


__plugin__ = CDNBG
