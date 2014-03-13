from livestreamer.exceptions import PluginError, NoStreamsError
from livestreamer.packages.flashmedia import AMFPacket, AMFMessage
from livestreamer.packages.flashmedia.types import AMF3ObjectBase
from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http
from livestreamer.stream import AkamaiHDStream

from io import BytesIO
from operator import attrgetter

import re


STREAM_NAMES = ["360p", "480p", "720p", "1080p"]


@AMF3ObjectBase.register("com.brightcove.experience.ViewerExperienceRequest")
class ViewerExperienceRequest(AMF3ObjectBase):
    __members__ = ["deliveryType", "TTLToken", "contentOverrides", "playerKey", "experienceId", "URL"]

    def __init__(self, URL, contentOverrides, experienceId, playerKey, TTLToken=""):
        self.URL = URL
        self.deliveryType = float(0)
        self.contentOverrides = contentOverrides
        self.experienceId = experienceId
        self.playerKey = playerKey
        self.TTLToken = TTLToken


@AMF3ObjectBase.register("com.brightcove.experience.ContentOverride")
class ContentOverride(AMF3ObjectBase):
    __members__ = ["contentIds", "contentType", "featuredId", "contentRefId",
                   "featuredRefId", "contentRefIds", "contentId", "target"]

    def __init__(self, contentId, contentType=0, target="videoPlayer"):
        self.contentType = contentType
        self.contentId = contentId
        self.target = target
        self.contentIds = None
        self.contentRefId = None
        self.contentRefIds = None
        self.contentType = 0
        self.featuredId = float(0)
        self.featuredRefId = None


class AzubuTV(Plugin):
    AMFGateway = "http://c.brightcove.com/services/messagebroker/amf"
    AMFMessagePrefix = "a9ab2f3d388a5169fc674c2ed57081c3d9c88158"

    @classmethod
    def can_handle_url(self, url):
        return "azubu.tv" in url

    def _create_amf_request(self, key, video_player, player_id):
        content_override = ContentOverride(int(video_player))
        viewer_exp_req = ViewerExperienceRequest(self.url,
                                                [content_override],
                                                int(player_id), key)

        req = AMFPacket(version=3)
        req.messages.append(AMFMessage(
            "com.brightcove.experience.ExperienceRuntimeFacade.getDataForExperience",
            "/1",
            [self.AMFMessagePrefix, viewer_exp_req]
        ))

        return req

    def _send_amf_request(self, req, key):
        headers = { "content-type": "application/x-amf" }
        res = http.post(self.AMFGateway, data=bytes(req.serialize()),
                        headers=headers, params=dict(playerKey=key))

        return AMFPacket.deserialize(BytesIO(res.content))

    def _get_player_params(self):
        res = http.get(self.url)

        match = re.search("<param name=\"playerKey\" value=\"(.+)\" />", res.text)
        if not match:
            raise PluginError("Missing key 'playerKey' in player params")

        key = match.group(1)

        match = re.search("<param name=\"@videoPlayer\" value=\"(\d+)\" />", res.text)
        if not match:
            raise PluginError("Missing key 'videoPlayer' in player params")

        video_player = match.group(1)

        match = re.search("<param name=\"playerID\" value=\"(\d+)\" />", res.text)
        if not match:
            raise PluginError("Missing key 'playerID' in player params")

        player_id = match.group(1)

        match = re.search("<!-- live on -->", res.text)
        is_live = not not match

        return key, video_player, player_id, is_live

    def _parse_result(self, res):
        streams = {}

        if not hasattr(res, "programmedContent"):
            raise PluginError("Invalid result")

        player = res.programmedContent["videoPlayer"]

        if not hasattr(player, "mediaDTO"):
            raise PluginError("Invalid result")

        renditions = sorted(player.mediaDTO.renditions.values(),
                            key=attrgetter("encodingRate"))

        for stream_name, rendition in zip(STREAM_NAMES, renditions):
            stream = AkamaiHDStream(self.session, rendition.defaultURL)
            streams[stream_name] = stream

        return streams

    def _get_streams(self):
        key, video_player, player_id, is_live = self._get_player_params()

        if not is_live:
            raise NoStreamsError(self.url)

        req = self._create_amf_request(key, video_player, player_id)
        res = self._send_amf_request(req, key)

        streams = {}
        for message in res.messages:
            if message.target_uri == "/1/onResult":
                streams = self._parse_result(message.value)

        return streams

__plugin__ = AzubuTV
