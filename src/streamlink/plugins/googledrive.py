"""
$description Stream videos stored in Google Drive.
$url docs.google.com
$url drive.google.com
$type vod
"""

import logging
import re
from urllib.parse import parse_qsl

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.stream.http import HTTPStream


log = logging.getLogger(__name__)


@pluginmatcher(
    re.compile(r"https?://(?:drive|docs)\.google\.com/file/d/([^/]+)/?"),
)
class GoogleDocs(Plugin):
    api_url = "https://docs.google.com/get_video_info"

    def _get_streams(self):
        docid = self.match.group(1)
        log.debug("Google Docs ID: {0}".format(docid))
        res = self.session.http.get(self.api_url, params=dict(docid=docid))
        data = dict(parse_qsl(res.text))

        if data["status"] == "ok":
            fmts = dict([s.split("/")[:2] for s in data["fmt_list"].split(",")])
            streams = [s.split("|") for s in data["fmt_stream_map"].split(",")]
            for qcode, url in streams:
                _, h = fmts[qcode].split("x")
                yield "{0}p".format(h), HTTPStream(self.session, url)
        else:
            log.error("{0} (ID: {1})".format(data["reason"], docid))


__plugin__ = GoogleDocs
