import re

from streamlink.plugin import Plugin
from streamlink.plugins.brightcove import BrightcovePlayer
from streamlink.stream import RTMPStream


class AlJazeeraEnglish(Plugin):
    url_re = re.compile(r"https?://(?:\w+\.)?aljazeera\.com")
    account_id = 665003303001
    render_re = re.compile(r'''RenderPagesVideo\((?P<q>['"])(?P<id>\d+)(?P=q)''')  # VOD
    video_id_re = re.compile(r'''videoId=(?P<id>\d+)["']''')  # Live

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        res = self.session.http.get(self.url)

        # check two different styles to include the video id in the page
        video_id_m = self.render_re.search(res.text) or self.video_id_re.search(res.text)
        video_id = video_id_m and video_id_m.group("id")

        if not video_id:
            self.logger.error("Could not find a video ID on this page")
            return

        # Use BrightcovePlayer class to get the streams
        self.logger.debug("Found video ID: {0}", video_id)
        bp = BrightcovePlayer(self.session, self.account_id)

        for q, s in bp.get_streams(video_id):
            # RTMP Streams are listed, but they do not appear to work
            if not isinstance(s, RTMPStream):
                yield q, s


__plugin__ = AlJazeeraEnglish
