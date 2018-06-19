import logging
import re

from streamlink.compat import urljoin
from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.plugin.api.utils import itertags
from streamlink.stream import HLSStream, DASHStream

log = logging.getLogger(__name__)


class VRTbe(Plugin):
    _url_re = re.compile(r'''https?://www\.vrt\.be/vrtnu/(?:kanalen/(?P<channel>[^/]+)|\S+)''')

    _stream_schema = validate.Schema(
        validate.any({
            "code": validate.text,
            "message": validate.text
        },
        {
            "drm": validate.any(None, validate.text),
            'targetUrls': [{
                'type': validate.text,
                'url': validate.text
            }],
        })
    )

    _token_schema = validate.Schema({
        "vrtPlayerToken": validate.text
    }, validate.get("vrtPlayerToken"))

    api_url = "https://api.vuplay.co.uk/"

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url)

    def _get_api_info(self, page):
        for div in itertags(page.text, 'div'):
            if div.attributes.get("class") == "vrtvideo":
                api_base = div.attributes.get("data-mediaapiurl") + "/"

                data = {"token_url": urljoin(api_base, "tokens")}
                if div.attributes.get("data-videotype") == "live":
                    data["stream_url"] = urljoin(urljoin(api_base, "videos/"), div.attributes.get("data-livestream"))
                else:
                    resource = "{0}%24{1}".format(div.attributes.get("data-publicationid"), div.attributes.get("data-videoid"))
                    data["stream_url"] = urljoin(urljoin(api_base, "videos/"), resource)
                return data

    def _get_streams(self):
        page = self.session.http.get(self.url)
        api_info = self._get_api_info(page)

        if not api_info:
            log.error("Could not find API info in page")
            return

        token_res = self.session.http.post(api_info["token_url"])
        token = self.session.http.json(token_res, schema=self._token_schema)

        log.debug("Got token: {0}".format(token))
        log.debug("Getting stream data: {0}".format(api_info["stream_url"]))
        res = self.session.http.get(api_info["stream_url"],
                                    params={
                                        "vrtPlayerToken": token,
                                        "client": "vrtvideo"
                                    }, raise_for_status=False)
        data = self.session.http.json(res, schema=self._stream_schema)

        if "code" in data:
            log.error("{0} ({1})".format(data['message'], data['code']))
            return

        log.debug("Streams have {0}DRM".format("no " if not data["drm"] else ""))

        for target in data["targetUrls"]:
            if data["drm"]:
                if target["type"] == "hls_aes":
                    for s in HLSStream.parse_variant_playlist(self.session, target["url"]).items():
                        yield s
            elif target["type"] == "hls":
                for s in HLSStream.parse_variant_playlist(self.session, target["url"]).items():
                    yield s
            elif target["type"] == "mpeg_dash":
                for s in DASHStream.parse_manifest(self.session, target["url"]).items():
                    yield s


__plugin__ = VRTbe
