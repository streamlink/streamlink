"""
$description Russian live-streaming and video hosting social platform.
$url vk.com
$type live, vod
"""

import logging
import re
from hashlib import md5
from urllib.parse import parse_qsl, unquote, urlparse

from streamlink.exceptions import NoStreamsError
from streamlink.plugin import Plugin, PluginError, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.dash import DASHStream
from streamlink.stream.hls import HLSStream
from streamlink.utils.url import update_qsd


log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:\w+\.)?vk\.com/videos?(?:\?z=video)?(?P<video_id>-?\d+_\d+)",
))
@pluginmatcher(re.compile(
    r"https?://(\w+\.)?vk\.com/.+",
))
class VK(Plugin):
    API_URL = "https://vk.com/al_video.php"
    HASH_COOKIE = "hash429"

    def _get_cookies(self):
        def on_response(res, **kwargs):
            if res.headers.get("x-waf-redirect") == "1":
                if not res.headers.get("X-WAF-Backend-Status"):
                    log.debug("Getting WAF cookie")
                    cookie = res.cookies.get(self.HASH_COOKIE)
                    key = md5(cookie.encode("utf-8")).hexdigest()
                    res.headers["Location"] = update_qsd(res.headers["Location"], qsd={"key": key})
                    return res
                elif res.headers.get("X-WAF-Backend-Status") == "challenge_success":
                    self.session.http.cookies.update(res.cookies)
                    return res

        self.session.http.get("https://vk.com/", hooks={"response": on_response})

    def _has_video_id(self):
        return any(self.matches[:-1])

    def follow_vk_redirect(self):
        if self._has_video_id():
            return

        try:
            parsed_url = urlparse(self.url)
            true_path = next(unquote(v).split("/")[0] for k, v in parse_qsl(parsed_url.query) if k == "z" and len(v) > 0)
            self.url = f"{parsed_url.scheme}://{parsed_url.netloc}/{true_path}"
            if self._has_video_id():
                return
        except StopIteration:
            pass

        try:
            self.url = self.session.http.get(self.url, schema=validate.Schema(
                validate.parse_html(),
                validate.xml_xpath_string(".//head/meta[@property='og:url'][@content]/@content"),
                str,
            ))
        except PluginError:
            pass
        if self._has_video_id():
            return

        raise NoStreamsError

    def _get_streams(self):
        self._get_cookies()
        self.follow_vk_redirect()

        video_id = self.match.group("video_id")
        if not video_id:
            return

        log.debug(f"Video ID: {video_id}")
        try:
            data = self.session.http.post(
                self.API_URL,
                params={"act": "show"},
                data={"act": "show", "al": "1", "video": video_id},
                headers={"Referer": self.url},
                schema=validate.Schema(
                    validate.transform(lambda text: re.sub(r"^\s*<!--\s*", "", text)),
                    validate.parse_json(),
                    {"payload": list},
                    validate.get(("payload", -1)),
                    list,
                    validate.get(-1),
                    {"player": {"params": [dict]}},
                    validate.get(("player", "params", 0)),
                    {
                        validate.optional("hls"): validate.url(),
                        validate.optional("manifest"): validate.startswith("<?xml"),
                        validate.optional("md_author"): validate.any(str, None),
                        validate.optional("md_title"): validate.any(str, None),
                    },
                ),
            )
        except PluginError:
            log.error("Could not parse API response")
            return

        self.id = video_id
        self.author = data.get("md_author")
        self.title = data.get("md_title")

        hls = data.get("hls")
        if hls:
            return HLSStream.parse_variant_playlist(self.session, hls)

        dash_manifest = data.get("manifest")
        if dash_manifest:
            return DASHStream.parse_manifest(self.session, dash_manifest)


__plugin__ = VK
