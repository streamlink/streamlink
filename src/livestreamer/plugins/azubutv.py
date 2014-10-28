import re

from io import BytesIO
from time import sleep

from livestreamer.exceptions import PluginError
from livestreamer.packages.flashmedia import AMFPacket, AMFMessage
from livestreamer.packages.flashmedia.types import AMF3ObjectBase
from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http, validate
from livestreamer.stream import AkamaiHDStream

AMF_GATEWAY = "http://c.brightcove.com/services/messagebroker/amf"
AMF_MESSAGE_PREFIX = "af6b88c640c8d7b4cc75d22f7082ad95603bc627"
STREAM_NAMES = ["360p", "480p", "720p", "source"]
HTTP_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/36.0.1944.9 Safari/537.36")
}

_url_re = re.compile("http(s)?://(\w+\.)?azubu.tv/[^/]+")

_viewerexp_schema = validate.Schema(
    validate.attr({
        "programmedContent": {
            "videoPlayer": validate.attr({
                "mediaDTO": validate.attr({
                    "renditions": {
                        int: validate.attr({
                            "encodingRate": int,
                            "defaultURL": validate.text
                        })
                    }
                })
            })
        }
    })
)


@AMF3ObjectBase.register("com.brightcove.experience.ViewerExperienceRequest")
class ViewerExperienceRequest(AMF3ObjectBase):
    __members__ = ["contentOverrides",
                   "experienceId",
                   "URL",
                   "playerKey",
                   "deliveryType",
                   "TTLToken"]

    def __init__(self, URL, contentOverrides, experienceId, playerKey, TTLToken=""):
        self.URL = URL
        self.deliveryType = float("nan")
        self.contentOverrides = contentOverrides
        self.experienceId = experienceId
        self.playerKey = playerKey
        self.TTLToken = TTLToken


@AMF3ObjectBase.register("com.brightcove.experience.ContentOverride")
class ContentOverride(AMF3ObjectBase):
    __members__ = ["featuredRefId",
                   "contentRefIds",
                   "contentId",
                   "contentType",
                   "contentIds",
                   "featuredId",
                   "contentRefId",
                   "target"]

    def __init__(self, contentId=float("nan"), contentRefId=None, contentType=0,
                 target="videoPlayer"):
        self.contentType = contentType
        self.contentId = contentId
        self.target = target
        self.contentIds = None
        self.contentRefId = contentRefId
        self.contentRefIds = None
        self.contentType = 0
        self.featuredId = float("nan")
        self.featuredRefId = None


class AzubuTV(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    @classmethod
    def stream_weight(cls, stream):
        if stream == "source":
            weight = 1080
        else:
            weight, group = Plugin.stream_weight(stream)

        return weight, "azubutv"

    def _create_amf_request(self, key, video_player, player_id):
        if video_player.startswith("ref:"):
            content_override = ContentOverride(contentRefId=video_player[4:])
        else:
            content_override = ContentOverride(contentId=int(video_player))
        viewer_exp_req = ViewerExperienceRequest(self.url,
                                                [content_override],
                                                int(player_id), key)

        req = AMFPacket(version=3)
        req.messages.append(AMFMessage(
            "com.brightcove.experience.ExperienceRuntimeFacade.getDataForExperience",
            "/1",
            [AMF_MESSAGE_PREFIX, viewer_exp_req]
        ))

        return req

    def _send_amf_request(self, req, key):
        headers = {
            "content-type": "application/x-amf"
        }
        res = http.post(AMF_GATEWAY, data=bytes(req.serialize()),
                        headers=headers, params=dict(playerKey=key))

        return AMFPacket.deserialize(BytesIO(res.content))

    def _get_player_params(self, retries=5):
        try:
            res = http.get(self.url, headers=HTTP_HEADERS)
        except PluginError as err:
            # The server sometimes gives us 404 for no reason
            if "404" in str(err) and retries:
                sleep(1)
                return self._get_player_params(retries - 1)
            else:
                raise

        match = re.search("<param name=\"playerKey\" value=\"(.+)\" />", res.text)
        if not match:
            # The HTML returned sometimes doesn't contain the parameters
            if not retries:
                raise PluginError("Missing key 'playerKey' in player params")
            else:
                sleep(1)
                return self._get_player_params(retries - 1)

        key = match.group(1)
        match = re.search("AZUBU.setVar\(\"firstVideoRefId\", \"(.+)\"\);", res.text)
        if not match:
            # The HTML returned sometimes doesn't contain the parameters
            if not retries:
                raise PluginError("Unable to find video reference")
            else:
                sleep(1)
                return self._get_player_params(retries - 1)

        video_player = "ref:" + match.group(1)
        match = re.search("<param name=\"playerID\" value=\"(\d+)\" />", res.text)
        if not match:
            # The HTML returned sometimes doesn't contain the parameters
            if not retries:
                raise PluginError("Missing key 'playerID' in player params")
            else:
                sleep(1)
                return self._get_player_params(retries - 1)

        player_id = match.group(1)
        match = re.search("<!-- live on -->", res.text)
        if not match:
            match = re.search("<div id=\"channel_live\">", res.text)
        is_live = not not match

        return key, video_player, player_id, is_live

    def _parse_result(self, res):
        res = _viewerexp_schema.validate(res)
        player = res.programmedContent["videoPlayer"]
        renditions = sorted(player.mediaDTO.renditions.values(),
                            key=lambda r: r.encodingRate or 100000000)

        streams = {}
        for stream_name, rendition in zip(STREAM_NAMES, renditions):
            stream = AkamaiHDStream(self.session, rendition.defaultURL)
            streams[stream_name] = stream

        return streams

    def _get_streams(self):
        key, video_player, player_id, is_live = self._get_player_params()

        if not is_live:
            return

        req = self._create_amf_request(key, video_player, player_id)
        res = self._send_amf_request(req, key)

        streams = {}
        for message in res.messages:
            if message.target_uri == "/1/onResult":
                streams = self._parse_result(message.value)

        return streams

__plugin__ = AzubuTV
