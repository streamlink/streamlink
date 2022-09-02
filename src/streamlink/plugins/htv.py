"""
$description Vietnamese live TV channels owned by the People's Committee of Ho Chi Minh City.
$url htv.com.vn
$type live
$region Vietnam
"""

import logging
import re
from datetime import date

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?htv\.com\.vn/truc-tuyen(?:\?channel=(?P<channel>\w+)&?|$)"
))
class HTV(Plugin):
    def get_channels(self):
        data = self.session.http.get(self.url, schema=validate.Schema(
            validate.parse_html(),
            validate.xml_xpath(".//*[contains(@class,'channel-list')]//a[@data-id][@data-code]"),
            [
                validate.union_get("data-id", "data-code"),
            ],
        ))

        return dict(data)

    def _get_streams(self):
        channels = self.get_channels()

        if not channels:
            log.error("No channels found")
            return

        log.debug(f"channels={channels}")

        channel_id = self.match.group("channel")
        if channel_id is None:
            channel_id, channel_code = next(iter(channels.items()))
        elif channel_id in channels:
            channel_code = channels[channel_id]
        else:
            log.error(f"Unknown channel ID: {channel_id}")
            return

        log.info(f"Channel: {channel_code}")

        json = self.session.http.post(
            "https://www.htv.com.vn/HTVModule/Services/htvService.aspx",
            data={
                "method": "GetScheduleList",
                "channelid": channel_id,
                "template": "AjaxSchedules.xslt",
                "channelcode": channel_code,
                "date": date.today().strftime("%d-%m-%Y"),
            },
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "success": bool,
                    "chanelUrl": validate.url(),
                },
            ),
        )

        if not json["success"]:
            log.error("API error: success not true")
            return

        hls_url = self.session.http.get(
            json["chanelUrl"],
            headers={"Referer": self.url},
            schema=validate.Schema(
                validate.parse_html(),
                validate.xml_xpath_string(".//script[contains(text(), 'playlist.m3u8')]/text()"),
                validate.none_or_all(
                    re.compile(r"""var\s+iosUrl\s*=\s*(?P<q>")(?P<url>.+?)(?P=q)"""),
                    validate.none_or_all(
                        validate.get("url"),
                        validate.url(),
                    ),
                ),
            ),
        )

        if hls_url:
            return HLSStream.parse_variant_playlist(
                self.session,
                hls_url,
                headers={"Referer": "https://hplus.com.vn/"},
            )


__plugin__ = HTV
