import re

from streamlink import PluginError
from streamlink.plugin.api import http, validate
from streamlink.plugin.api import useragents
from streamlink.stream import HLSStream
from streamlink.stream import HTTPStream
from streamlink.stream import RTMPStream


class BrightcovePlayer(object):
    player_page = "http://players.brightcove.net/{account_id}/{player_id}/index.html"
    api_url = "https://edge.api.brightcove.com/playback/v1/"

    policy_key_re = re.compile(r'''policyKey\s*:\s*(?P<q>['"])(?P<key>.*?)(?P=q)''')

    schema = validate.Schema({
        "sources": [{
            validate.optional("height"): validate.any(int, None),
            validate.optional("avg_bitrate"): validate.any(int, None),
            validate.optional("src"): validate.url(),
            validate.optional("app_name"): validate.url(scheme="rtmp"),
            validate.optional("stream_name"): validate.text,
            validate.optional("type"): validate.text
        }]
    })

    def __init__(self, session, account_id, player_id="default_default"):
        self.session = session
        self.logger = session.logger.new_module("plugins.brightcove")
        self.account_id = account_id
        self.player_id = player_id

    def player_url(self, video_id):
        return self.player_page.format(account_id=self.account_id,
                                       player_id=self.player_id,
                                       params=dict(videoId=video_id))

    def video_info(self, video_id, policy_key):
        url = "{base}accounts/{account_id}/videos/{video_id}".format(base=self.api_url,
                                                                     account_id=self.account_id,
                                                                     video_id=video_id)
        res = http.get(url,
                       headers={
                           "User-Agent": useragents.CHROME,
                           "Referer": self.player_url(video_id),
                           "Accept": "application/json;pk={0}".format(policy_key)
                       })
        return http.json(res, schema=self.schema)

    def policy_key(self, video_id):
        # Get the embedded player page
        res = http.get(self.player_url(video_id))

        policy_key_m = self.policy_key_re.search(res.text)
        policy_key = policy_key_m and policy_key_m.group("key")
        if not policy_key:
            raise PluginError("Could not find Brightcove policy key")

        return policy_key

    def get_streams(self, video_id):
        policy_key = self.policy_key(video_id)
        self.logger.debug("Found policy key: {0}", policy_key)
        data = self.video_info(video_id, policy_key)

        for source in data.get("sources"):
            # determine quality name
            if source.get("height"):
                q = "{0}p".format(source.get("height"))
            elif source.get("avg_bitrate"):
                q = "{0}k".format(source.get("avg_bitrate") // 1000)
            else:
                q = "live"

            if ((source.get("type") == "application/x-mpegURL" and source.get("src")) or
                    (source.get("src") and source.get("src").endswith(".m3u8"))):
                for s in HLSStream.parse_variant_playlist(self.session, source.get("src")).items():
                    yield s
            elif source.get("app_name"):
                s = RTMPStream(self.session,
                               {"rtmp": source.get("app_name"),
                                "playpath": source.get("stream_name")})
                yield q, s
            elif source.get("src") and source.get("src").endswith(".mp4"):
                yield q, HTTPStream(self.session, source.get("src"))

