import logging
import re

from lxml.etree import HTML, _Element as Element

from streamlink.compat import parse_qsl, urlparse
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream, HTTPStream
from streamlink.utils import parse_json

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?dw\.com/"
))
class DeutscheWelle(Plugin):
    DEFAULT_CHANNEL = "1"
    API_URL = "https://www.dw.com/playersources/v-{media_id}?hls=true"

    def _find_metadata(self, elem):
        # type: (Element)
        self.author = elem.xpath("string(.//input[@name='channel_name'][1]/@value)") or None
        self.title = elem.xpath("string(.//input[@name='media_title'][1]/@value)") or None

    def _get_live_streams(self, root):
        # type: (Element)
        # check if a different language has been selected
        channel = (
            dict(parse_qsl(urlparse(self.url).query)).get("channel")
            or root.xpath("string(.//a[@data-id][@class='ici'][1]/@data-id)")
            or self.DEFAULT_CHANNEL
        )
        log.debug("Using channel ID: {0}".format(channel))

        media_item = root.find(".//*[@data-channel-id='{0}']".format(channel))
        if media_item is None:
            return

        self._find_metadata(media_item)
        stream_url = media_item.xpath("string(.//input[@name='file_name'][1]/@value)")
        if stream_url:
            return HLSStream.parse_variant_playlist(self.session, stream_url)

    def _get_vod_streams(self, root):
        # type: (Element)
        media_id = root.xpath("string(.//input[@type='hidden'][@name='media_id'][1]/@value)")
        if not media_id:
            return

        self._find_metadata(root)
        api_url = self.API_URL.format(media_id=media_id)
        stream_url = self.session.http.get(api_url, schema=validate.Schema(
            validate.transform(parse_json),
            [{"file": validate.url()}],
            validate.get((0, "file"))
        ))
        return HLSStream.parse_variant_playlist(self.session, stream_url)

    def _get_audio_streams(self, root):
        # type: (Element)
        self._find_metadata(root)
        file_name = root.xpath("string(.//input[@type='hidden'][@name='file_name'][1]/@value)")
        if file_name:
            yield "audio", HTTPStream(self.session, file_name)

    def _get_streams(self):
        root = self.session.http.get(self.url, schema=validate.Schema(
            validate.transform(HTML)
        ))
        player_type = root.xpath("string(.//input[@type='hidden'][@name='player_type'][1]/@value)")

        if player_type == "dwlivestream":
            return self._get_live_streams(root)
        elif player_type == "video":
            return self._get_vod_streams(root)
        elif player_type == "audio":
            return self._get_audio_streams(root)


__plugin__ = DeutscheWelle
