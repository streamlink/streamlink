from __future__ import print_function

import logging
import re

from streamlink.compat import urljoin
from streamlink.plugin import Plugin
from streamlink.stream import DASHStream

log = logging.getLogger(__name__)


class TF1(Plugin):
    url_re = re.compile(r"https?://(?:www\.)?(?:tf1\.fr/([\w-]+)/direct|(lci).fr/direct)/?")
    api_url_base = "https://delivery.tf1.fr/mytf1-wrd/"
    token = "07e45841-a17a-47cf-af64-a42311bdcc3d"

    def api_call(self, channel):
        url = urljoin(self.api_url_base, "L_"+channel.upper())
        req = self.session.http.get(url, params=dict(token=self.token))
        return self.session.http.json(req)

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        m = self.url_re.match(self.url)
        if m:
            channel = m.group(1) or m.group(2)
            self.logger.debug("Found channel {0}", channel)
            data = self.api_call(channel)

            if data.get("error"):
                log.error("Failed to get stream for {0}: {error} ({code})".format(channel, **data))
            else:
                log.debug("Got {format} stream {url}".format(**data))
                if data["format"] == "dash":
                    for s in DASHStream.parse_manifest(self.session, data["url"]).items():
                        yield s


__plugin__ = TF1
