import re

from json import loads
from streamlink.plugin import Plugin
from streamlink.stream import HTTPStream


class Canvas(Plugin):
    url_re = re.compile(r"https?://(.*)\.instructure\.com/media_objects/([^/]+)")
    api_url = "https://{subdomain}.instructure.com/media_objects/{media_object_id}/info"

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        matches = self.url_re.match(self.url)
        subdomain = matches.group(1)
        moid = matches.group(2)
        self.logger.debug("Media Object ID: {0}", moid)
        res = self.session.http.get(self.api_url.format(subdomain=subdomain,media_object_id=moid))
        data = loads(res.text)

        if "media_sources" in data.keys():
            for stream in data["media_sources"]:
                yield "{0}p".format(stream["height"]), HTTPStream(self.session, stream["url"])
        else:
            self.logger.error("No stream links found. (ID: {0})", moid)


__plugin__ = Canvas
