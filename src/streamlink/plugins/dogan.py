"""
$description Turkish live TV channels and video on-demand service from Dogan Group, including CNN Turk and Kanal D.
$url cnnturk.com
$url dreamturk.com.tr
$url dreamtv.com.tr
$url kanald.com.tr
$url teve2.com.tr
$type live, vod
"""

import logging
import re
from urllib.parse import urljoin

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(r"""
    https?://(?:www\.)?
    (?:
        cnnturk\.com/(?:action/embedvideo/|canli-yayin|tv-cnn-turk|video/)|
        dreamturk\.com\.tr/(?:canli|canli-yayin-izle|dream-turk-ozel/|programlar/)|
        dreamtv\.com\.tr/dream-ozel/|
        kanald\.com\.tr/|
        teve2\.com\.tr/(?:canli-yayin|diziler/|embed/|filmler/|programlar/)
    )
""", re.VERBOSE))
class Dogan(Plugin):
    playerctrl_re = re.compile(r'''<div\s+id="video-element".*?>''', re.DOTALL)
    data_id_re = re.compile(r'''data-id=(?P<quote>["'])/?(?P<id>\w+)(?P=quote)''')
    content_id_re = re.compile(r'"content[Ii]d",\s*"(\w+)"')
    item_id_re = re.compile(r"_itemId\s+=\s+'(\w+)';")
    content_api = "/actions/media?id={id}"
    dream_api = "/actions/content/media/{id}"
    new_content_api = "/action/media/{id}"
    content_api_schema = validate.Schema(
        {
            "data": {
                "id": str,
                "media": {
                    "link": {
                        validate.optional("defaultServiceUrl"): validate.any(validate.url(), ""),
                        validate.optional("serviceUrl"): validate.any(validate.url(), ""),
                        "securePath": str,
                    },
                },
            },
        },
        validate.get("data"),
        validate.get("media"),
        validate.get("link"),
    )
    new_content_api_schema = validate.Schema(
        {
            "Media": {
                "Link": {
                    "ContentId": str,
                    validate.optional("DefaultServiceUrl"): validate.any(validate.url(), ""),
                    validate.optional("ServiceUrl"): validate.any(validate.url(), ""),
                    "SecurePath": str,
                },
            },
        },
        validate.get("Media"),
        validate.get("Link"),
    )

    def _get_content_id(self):
        res = self.session.http.get(self.url)
        # find the contentId
        content_id_m = self.content_id_re.search(res.text)
        if content_id_m:
            log.debug("Found contentId by contentId regex")
            return content_id_m.group(1)

        # find the PlayerCtrl div
        player_ctrl_m = self.playerctrl_re.search(res.text)
        if player_ctrl_m:
            # extract the content id from the player control data
            player_ctrl_div = player_ctrl_m.group(0)
            content_id_m = self.data_id_re.search(player_ctrl_div)
            if content_id_m:
                log.debug("Found contentId by player data-id regex")
                return content_id_m.group("id")

        # find the itemId var
        item_id_m = self.item_id_re.search(res.text)
        if item_id_m:
            log.debug("Found contentId by itemId regex")
            return item_id_m.group(1)

    def _get_new_content_hls_url(self, content_id, api_url):
        log.debug("Using new content API url")
        d = self.session.http.get(urljoin(self.url, api_url.format(id=content_id)))
        d = self.session.http.json(d, schema=self.new_content_api_schema)

        if d["DefaultServiceUrl"] == "https://www.kanald.com.tr":
            self.url = d["DefaultServiceUrl"]
            return self._get_content_hls_url(content_id)
        else:
            if d["SecurePath"].startswith("http"):
                return d["SecurePath"]
            else:
                return urljoin((d["ServiceUrl"] or d["DefaultServiceUrl"]), d["SecurePath"])

    def _get_content_hls_url(self, content_id):
        d = self.session.http.get(urljoin(self.url, self.content_api.format(id=content_id)))
        d = self.session.http.json(d, schema=self.content_api_schema)

        return urljoin((d["serviceUrl"] or d["defaultServiceUrl"]), d["securePath"])

    def _get_hls_url(self, content_id):
        # make the api url relative to the current domain
        if "cnnturk.com" in self.url or "teve2.com.tr" in self.url:
            return self._get_new_content_hls_url(content_id, self.new_content_api)
        elif "dreamturk.com.tr" in self.url or "dreamtv.com.tr" in self.url:
            return self._get_new_content_hls_url(content_id, self.dream_api)
        else:
            return self._get_content_hls_url(content_id)

    def _get_streams(self):
        content_id = self._get_content_id()
        if content_id:
            log.debug(f"Loading content: {content_id}")
            hls_url = self._get_hls_url(content_id)
            return HLSStream.parse_variant_playlist(self.session, hls_url)
        else:
            log.error("Could not find the contentId for this stream")


__plugin__ = Dogan
