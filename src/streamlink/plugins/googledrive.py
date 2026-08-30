"""
$description Stream videos stored in Google Drive.
$url docs.google.com
$url drive.google.com
$type vod
"""

import re
from urllib.parse import parse_qsl

from streamlink.logger import getLogger
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.stream.http import HTTPStream


log = getLogger(__name__)


@pluginmatcher(
    re.compile(r"https?://(?:drive|docs)\.google\.com/file/d/([^/]+)/?"),
)
class GoogleDocs(Plugin):
    api_url = "https://docs.google.com/get_video_info"

    def _get_streams(self):
        docid = self.match.group(1)
        log.debug("Google Docs ID: %s", docid)
        res = self.session.http.get(self.api_url, params=dict(docid=docid))
        data = dict(parse_qsl(res.text))

        if data["status"] == "ok":
            fmts = dict([s.split("/")[:2] for s in data["fmt_list"].split(",")])
            streams = [s.split("|") for s in data["fmt_stream_map"].split(",")]
            for qcode, url in streams:
                _, h = fmts[qcode].split("x")
                yield f"{h}p", HTTPStream(self.session, url)
        else:
            log.error("%s (ID: %s)", data["reason"], docid)


__plugin__ = GoogleDocs
