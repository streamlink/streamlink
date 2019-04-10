from __future__ import print_function
import re

from streamlink.plugin import Plugin


class CanalSur(Plugin):
    url_re = re.compile(r"(?:https?://)?(?:www\.)?canalsur\.es/tv_directo-.*\.html")
    match_youtube = re.compile(r"src=\"(?P<url>(?:https?://)?(?:www\.)?youtube.com/embed/live_stream\?channel=[^\"]*)\"")

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        res = self.session.http.get(self.url)
        #print(res.text)
        m = self.match_youtube.search(res.text)
        if m:
            yt_url = m.group("url")
            print(yt_url)
            if yt_url:
                self.logger.debug("Deferring to YouTube plugin with URL: {0}".format(yt_url))
                return self.session.streams(yt_url)

__plugin__ = CanalSur