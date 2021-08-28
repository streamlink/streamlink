import logging
import re
from urllib.parse import parse_qsl, urlparse

from lxml.etree import HTML, _Element as Element

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

    author = None
    title = None

    def get_author(self):
        return self.author

    def get_title(self):
        return self.title

    def _find_metadata(self, elem: Element):
        self.author = elem.xpath("string(.//input[@name='channel_name'][1]/@value)") or None
        self.title = elem.xpath("string(.//input[@name='media_title'][1]/@value)") or None

    def _get_live_streams(self, root: Element):
        # check if a different language has been selected
        channel: str = (
            dict(parse_qsl(urlparse(self.url).query)).get("channel")
            or root.xpath("string(.//a[@data-id][@class='ici'][1]/@data-id)")
            or self.DEFAULT_CHANNEL
        )
        log.debug(f"Using channel ID: {channel}")

        media_item: Element = root.find(f".//*[@data-channel-id='{channel}']")
        if media_item is None:
            return

        self._find_metadata(media_item)
        stream_url: str = media_item.xpath("string(.//input[@name='file_name'][1]/@value)")
        if stream_url:
            return HLSStream.parse_variant_playlist(self.session, stream_url)

    def _get_vod_streams(self, root: Element):
        media_id: str = root.xpath("string(.//input[@type='hidden'][@name='media_id'][1]/@value)")
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

    def _get_audio_streams(self, root: Element):
        self._find_metadata(root)
        file_name: str = root.xpath("string(.//input[@type='hidden'][@name='file_name'][1]/@value)")
        if file_name:
            yield "audio", HTTPStream(self.session, file_name)

    def _get_streams(self):
        root = self.session.http.get(self.url, schema=validate.Schema(
            validate.transform(HTML)
        ))
        player_type: str = root.xpath("string(.//input[@type='hidden'][@name='player_type'][1]/@value)")

        if player_type == "dwlivestream":
            return self._get_live_streams(root)
        elif player_type == "video":
            return self._get_vod_streams(root)
        elif player_type == "audio":
            return self._get_audio_streams(root)


__plugin__ = DeutscheWelle
