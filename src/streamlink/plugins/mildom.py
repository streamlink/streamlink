import logging
import re

from streamlink.plugin import Plugin
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)


class Mildom(Plugin):

    _re_url = re.compile(r"""
        https?://(www\.)?mildom\.com/
        (?:
            playback/(\d+)(/(?P<video_id>(\d+)\-(\w+)))
            |
            (?P<channel_id>\d+)
        )
    """, re.VERBOSE)

    _VOD_API_URL = "https://cloudac.mildom.com/nonolive/videocontent/playback/getPlaybackDetail?v_id={}"

    _STATUS_API_URL = "https://cloudac.mildom.com/nonolive/gappserv/live/enterstudio?__platform=web&user_id={}"

    _LIVESERVER_API_URL = 'https://cloudac.mildom.com/nonolive/gappserv/live/liveserver'\
                          '?__platform=web&user_id=4253873&live_server_type=hls'

    @classmethod
    def can_handle_url(cls, url):
        return cls._re_url.match(url)

    def _get_vod_streams(self, video_id):
        res = self.session.http.get(self._VOD_API_URL.format(video_id))
        response_json = self.session.http.json(res)
        if response_json.get("code"):
            log.debug("Mildom API returned an error. Vod is probably invalid")
            return
        for stream in response_json["body"]["playback"]["video_link"]:
            yield stream["name"], HLSStream(self.session, stream["url"])

    def _get_live_streams(self, channel_id):
        # Get quality info and check if user is live1
        res = self.session.http.get(self._STATUS_API_URL.format(channel_id))
        response_json = self.session.http.json(res)
        if response_json.get("code"):
            log.debug("Mildom API returned an error")
            return
        if response_json["body"].get("anchor_live") != 11:
            log.debug("User doesn't appear to be live")
            return
        qualities = []
        for quality_info in response_json["body"]["ext"]["cmode_params"]:
            qualities.append((quality_info["name"], "_" + quality_info["cmode"] if quality_info["cmode"] != "raw" else ""))
        # Create stream URLs
        res = self.session.http.get(self._LIVESERVER_API_URL.format(channel_id))
        response_json = self.session.http.json(res)
        if response_json.get("code"):
            log.debug("Mildom API returned an error")
            return
        base_url = response_json["body"]["stream_server"] + "/" + str(channel_id) + "{}.m3u8"
        for quality in qualities:
            self.session.http.headers.update({"Referer": "https://www.mildom.com/"})
            yield quality[0], HLSStream(self.session, base_url.format(quality[1]))

    def _get_streams(self):
        match = self._re_url.match(self.url)
        channel_id = match.group("channel_id")
        video_id = match.group("video_id")
        if video_id:
            return self._get_vod_streams(video_id)
        else:
            return self._get_live_streams(channel_id)
        return


__plugin__ = Mildom
