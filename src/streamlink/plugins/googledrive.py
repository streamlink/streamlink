import logging
import re
from urllib.parse import parse_qsl

from streamlink.plugin import Plugin
from streamlink.stream import HTTPStream

log = logging.getLogger(__name__)


class GoogleDocs(Plugin):
    url_re = re.compile(r"https?://(?:drive|docs)\.google\.com/file/d/([^/]+)/?")
    api_url = "https://docs.google.com/get_video_info"

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        docid = self.url_re.match(self.url).group(1)
        log.debug("Google Docs ID: {0}".format(docid))
        res = self.session.http.get(self.api_url, params=dict(docid=docid))
        data = dict(parse_qsl(res.text))

        if data["status"] == "ok":
            fmts = dict([s.split('/')[:2] for s in data["fmt_list"].split(",")])
            streams = [s.split('|') for s in data["fmt_stream_map"].split(",")]
            for qcode, url in streams:
                _, h = fmts[qcode].split("x")
                yield "{0}p".format(h), HTTPStream(self.session, url)
        else:
            log.error("{0} (ID: {1})".format(data["reason"], docid))


__plugin__ = GoogleDocs
