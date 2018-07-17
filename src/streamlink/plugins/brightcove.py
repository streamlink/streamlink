import random
import re
import logging
from io import BytesIO

from streamlink import PluginError
from streamlink.packages.flashmedia import AMFMessage, AMFPacket
from streamlink.packages.flashmedia.types import AMF3ObjectBase
from streamlink.plugin import Plugin
from streamlink.plugin.api import validate, useragents
from streamlink.stream import HLSStream, HTTPStream, RTMPStream
from streamlink.compat import urlparse, parse_qsl, urlencode


@AMF3ObjectBase.register("com.brightcove.experience.ViewerExperienceRequest")
class ViewerExperienceRequest(AMF3ObjectBase):
    def __init__(self, experienceId, URL, playerKey, deliveryType, TTLToken, contentOverrides):
        self.experienceId = experienceId
        self.URL = URL
        self.playerKey = playerKey
        self.deliveryType = deliveryType
        self.TTLToken = TTLToken
        self.contentOverrides = contentOverrides


@AMF3ObjectBase.register("com.brightcove.experience.ContentOverride")
class ContentOverride(AMF3ObjectBase):
    def __init__(self, featuredRefId, contentRefIds, contentId, target="videoPlayer", contentIds=None,
                 contentType=0, featuredId=float('nan'), contentRefId=None):
        self.featuredRefId = featuredRefId
        self.contentRefIds = contentRefIds
        self.contentId = contentId
        self.target = target
        self.contentIds = contentIds
        self.contentType = contentType
        self.featuredId = featuredId
        self.contentRefId = contentRefId


class BrightcovePlayer(object):
    player_page = "http://players.brightcove.net/{account_id}/{player_id}/index.html"
    api_url = "https://edge.api.brightcove.com/playback/v1/"
    amf_broker = "http://c.brightcove.com/services/messagebroker/amf"

    policy_key_re = re.compile(r'''policyKey\s*:\s*(?P<q>['"])(?P<key>.*?)(?P=q)''')

    schema = validate.Schema({
        "sources": [{
            validate.optional("height"): validate.any(int, None),
            validate.optional("avg_bitrate"): validate.any(int, None),
            validate.optional("src"): validate.url(),
            validate.optional("app_name"): validate.any(
                validate.url(scheme="rtmp"),
                validate.url(scheme="rtmpe")
            ),
            validate.optional("stream_name"): validate.text,
            validate.optional("type"): validate.text
        }]
    })

    def __init__(self, session, account_id, player_id="default_default"):
        self.session = session
        self.logger = logging.getLogger("streamlink.plugins.brightcove")
        self.logger.debug("Creating player for account {0} (player_id={1})", account_id, player_id)
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
        res = self.session.http.get(url,
                       headers={
                           "User-Agent": useragents.CHROME,
                           "Referer": self.player_url(video_id),
                           "Accept": "application/json;pk={0}".format(policy_key)
                       })
        return self.session.http.json(res, schema=self.schema)

    def policy_key(self, video_id):
        # Get the embedded player page
        res = self.session.http.get(self.player_url(video_id))

        policy_key_m = self.policy_key_re.search(res.text)
        policy_key = policy_key_m and policy_key_m.group("key")
        if not policy_key:
            raise PluginError("Could not find Brightcove policy key")

        return policy_key

    def get_streams(self, video_id):
        self.logger.debug("Finding streams for video: {0}", video_id)
        policy_key = self.policy_key(video_id)
        self.logger.debug("Found policy key: {0}", policy_key)
        data = self.video_info(video_id, policy_key)
        headers = {"Referer": self.player_url(video_id)}

        for source in data.get("sources"):
            # determine quality name
            if source.get("height"):
                q = "{0}p".format(source.get("height"))
            elif source.get("avg_bitrate"):
                q = "{0}k".format(source.get("avg_bitrate") // 1000)
            else:
                q = "live"
            if ((source.get("type") == "application/x-mpegURL" and source.get("src")) or
                    (source.get("src") and ".m3u8" in source.get("src"))):
                for s in HLSStream.parse_variant_playlist(self.session, source.get("src"), headers=headers).items():
                    yield s
            elif source.get("app_name"):
                s = RTMPStream(self.session,
                               {"rtmp": source.get("app_name"),
                                "playpath": source.get("stream_name")})
                yield q, s
            elif source.get("src") and source.get("src").endswith(".mp4"):
                yield q, HTTPStream(self.session, source.get("src"), headers=headers)

    @classmethod
    def from_url(cls, session, url):
        purl = urlparse(url)
        querys = dict(parse_qsl(purl.query))

        account_id, player_id, _ = purl.path.lstrip("/").split("/", 3)
        video_id = querys.get("videoId")

        bp = cls(session, account_id=account_id, player_id=player_id)
        return bp.get_streams(video_id)

    @classmethod
    def from_player_key(cls, session, player_id, player_key, video_id, url=None):
        amf_message = AMFMessage("com.brightcove.experience.ExperienceRuntimeFacade.getDataForExperience",
                                 "/1",
                                 [
                                     ''.join(["{0:02x}".format(random.randint(0, 255)) for _ in range(20)]),  # random id
                                     ViewerExperienceRequest(experienceId=int(player_id),
                                                             URL=url or "",
                                                             playerKey=player_key,
                                                             deliveryType=float('nan'),
                                                             TTLToken="",
                                                             contentOverrides=[ContentOverride(
                                                                 featuredRefId=None,
                                                                 contentRefIds=None,
                                                                 contentId=int(video_id)
                                                             )])
                                 ])
        amf_packet = AMFPacket(version=3)
        amf_packet.messages.append(amf_message)

        res = self.session.http.post(cls.amf_broker,
                        headers={"Content-Type": "application/x-amf"},
                        data=amf_packet.serialize(),
                        params=dict(playerKey=player_key),
                        raise_for_status=False)
        data = AMFPacket.deserialize(BytesIO(res.content))
        result = data.messages[0].value
        bp = cls(session=session, account_id=int(result.publisherId))
        return bp.get_streams(video_id)


class Brightcove(Plugin):
    url_re = re.compile(r"https?://players.brightcove.net/.*?/index.html")

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        return BrightcovePlayer.from_url(self.session, self.url)


__plugin__ = Brightcove
