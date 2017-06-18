import re

import itertools

from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream
from streamlink.stream import HTTPStream
from streamlink.utils import parse_json


class Looch(Plugin):
    url_re = re.compile(r"https?://(?:www\.)?looch\.tv/channel/(?P<name>[^/]+)(/videos/(?P<video_id>\d+))?")

    api_base = "https://api.looch.tv"
    channel_api = api_base + "/channels/{name}"
    video_api = api_base + "/videos/{id}"

    playback_schema = validate.Schema({"weight": int, "uri": validate.url()})
    data_schema = validate.Schema({
        "type": validate.text,
        "attributes": {
            validate.optional("playback"): [playback_schema],
            validate.optional("resolution"): {"width": int, "height": int}
        }})
    channel_schema = validate.Schema(
        validate.transform(parse_json),
        {"included": validate.all(
            [data_schema],
            validate.filter(lambda x: x["type"] == "active_streams"),
            validate.map(lambda x: x["attributes"].get("playback")),
            validate.transform(lambda x: list(itertools.chain(*x)))
        ),
        }, validate.get("included"))
    video_schema = validate.Schema(
        validate.transform(parse_json),
        {"data": data_schema},
        validate.get("data"),
        validate.get("attributes"))

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_live_stream(self, channel):
        url = self.channel_api.format(name=channel)
        self.logger.debug("Channel API call: {0}", url)
        data = http.get(url, schema=self.channel_schema)
        self.logger.debug("Got {0} channel playback items", len(data))
        for playback in data:
            for s in HLSStream.parse_variant_playlist(self.session, playback["uri"]).items():
                yield s

    def _get_video_stream(self, video_id):
        url = self.video_api.format(id=video_id)
        self.logger.debug("Video API call: {0}", url)
        data = http.get(url, schema=self.video_schema)
        self.logger.debug("Got video {0} playback items", len(data["playback"]))
        res = data["resolution"]["height"]
        for playback in data["playback"]:
            yield "{0}p".format(res), HTTPStream(self.session, playback["uri"])


    def _get_streams(self):
        match = self.url_re.match(self.url)
        self.logger.debug("Matched URL: name={name}, video_id={video_id}", **match.groupdict())

        if match.group("video_id"):
            return self._get_video_stream(match.group("video_id"))
        elif match.group("name"):
            return self._get_live_stream(match.group("name"))


__plugin__ = Looch
