import logging
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import useragents, validate
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)


class Bigo(Plugin):
    _url_re = re.compile(r"^https?://(?:www\.)?bigo\.tv/[^/]+$")
    _video_re = re.compile(
        r"""videoSrc:\s?["'](?P<url>[^"']+)["']""",
        re.M)
    _id_re = re.compile(r"[^/]+(?=/$|$)")
    _video_info_schema = validate.Schema({
        "code": 0,
        "msg": "success",
        "data": {
            "videoSrc": validate.any(None, validate.url()),
            "wsUrl": validate.any(None, validate.url())
        }
    })
    api_url = "https://www.bigo.tv/OInterface/getVideoParam?bigoId="

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _get_streams(self):
        extract_id = self._id_re.search(self.url)
        url = "%s%s" %(self.api_url, extract_id.group(0))
        res = self.session.http.get(
            url,
            allow_redirects=True,
            headers={"User-Agent": useragents.IPHONE_6}
        )
        data = self.session.http.json(res, schema=self._video_info_schema)
        videomatch = data['data']['videoSrc']
        if not videomatch:
            log.error("No playlist found.")
            return

        videourl = videomatch
        log.debug("URL={0}".format(videourl))
        yield "live", HLSStream(self.session, videourl)


__plugin__ = Bigo
