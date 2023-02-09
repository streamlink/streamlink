"""
$description Live TV channels and video on-demand service from Deutsche Welle, a German public, state-owned broadcaster.
$url dw.com
$type live, vod
"""

import logging
import re
from urllib.parse import parse_qsl, urlparse

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream
from streamlink.stream.http import HTTPStream


log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?dw\.com/",
))
class DeutscheWelle(Plugin):
    DEFAULT_CHANNEL = "1"

    def _get_streams(self):
        root, channel = self.session.http.get(self.url, schema=validate.Schema(
            validate.parse_html(),
            validate.union((
                validate.xml_find("."),
                validate.xml_xpath_string(".//a[@data-id][@class='ici'][1]/@data-id"),
            )),
        ))

        # check if a different language has been selected
        channel = int(
            dict(parse_qsl(str(urlparse(self.url).query))).get("channel")
            or channel
            or self.DEFAULT_CHANNEL,
        )
        log.debug(f"Using channel ID: {channel}")

        schema = validate.Schema(
            validate.any(
                # find the video element of the selected channel ID first
                # node-sets are always ordered by the document order, so these queries can't be merged into one
                validate.all(
                    validate.xml_xpath(".//video[../@data-channel-id=$channel][1]", channel=channel),
                    # validate.xml_element() can't be used here, because it discards parent nodes of the cloned return value
                    lambda res: res is not None,
                    validate.get(0),
                ),
                # just get the first video element if the above query fails (no channel selection)
                validate.xml_find(".//video"),
            ),
            validate.union((
                validate.xml_xpath_string("./source[@src][@type='application/x-mpegURL'][1]/@src"),
                validate.xml_xpath_string("./source[@src][@type='audio/mpeg'][1]/@src"),
                validate.xml_xpath_string("(../@data-channel-id | ../@data-media-id)[1]"),
                validate.xml_xpath_string("../input[@name='media_title']/@value"),
                validate.all(
                    validate.xml_xpath_string("./@data-options"),
                    validate.none_or_all(
                        str,
                        validate.parse_json(),
                        {
                            "trackingInfo": {
                                validate.optional("channelName"): str,
                                validate.optional("mediaTitle"): str,
                            },
                        },
                        validate.get("trackingInfo"),
                        validate.union_get("channelName", "mediaTitle"),
                    ),
                ),
            )),
        )
        data = schema.validate(root)
        if not data:
            return

        hls, audio, self.id, self.title, metadata = data
        if metadata:
            self.author, mediaTitle = metadata
            self.title = self.title or mediaTitle

        if hls:
            return HLSStream.parse_variant_playlist(self.session, hls)
        if audio:
            return {"audio": HTTPStream(self.session, audio)}


__plugin__ = DeutscheWelle
