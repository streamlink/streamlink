"""
$description Global live-streaming and video hosting social platform.
$url facebook.com
$type live, vod
"""

import logging
import re
from urllib.parse import unquote_plus, urlencode

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.dash import DASHStream
from streamlink.stream.http import HTTPStream
from streamlink.utils.parse import parse_json

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(r"""
    https?://(?:www\.)?facebook
    (?:\.com|wkhpilnemxj7asaniu7vnjjbiltxjqhye3mhbshg7kx5tfyd\.onion)
    /[^/]+/(?:posts|videos)/(?P<video_id>\d+)
""", re.VERBOSE))
class Facebook(Plugin):
    _src_re = re.compile(r'''(sd|hd)_src["']?\s*:\s*(?P<quote>["'])(?P<url>.+?)(?P=quote)''')
    _dash_manifest_re = re.compile(r'''dash_manifest["']?\s*:\s*["'](?P<manifest>.+?)["'],''')
    _playlist_re = re.compile(r'''video:\[({url:".+?}\])''')
    _plurl_re = re.compile(r'''url:"(.*?)"''')
    _pc_re = re.compile(r'''pkg_cohort["']\s*:\s*["'](.+?)["']''')
    _rev_re = re.compile(r'''client_revision["']\s*:\s*(\d+),''')
    _dtsg_re = re.compile(r'''DTSGInitialData["'],\s*\[\],\s*{\s*["']token["']\s*:\s*["'](.+?)["']''')
    _DEFAULT_PC = "PHASED:DEFAULT"
    _DEFAULT_REV = 4681796
    _TAHOE_URL = "https://www.facebook.com/video/tahoe/async/{0}/?chain=true&isvideo=true&payloadtype=primary"

    def _parse_streams(self, res):
        stream_url = validate.Schema(
            validate.parse_html(),
            validate.xml_xpath_string(".//head/meta[@property='og:video:url'][@content][1]/@content")
        ).validate(res.text)
        if not stream_url:
            log.debug("No meta og:video:url")
        elif ".mpd" in stream_url:
            yield from DASHStream.parse_manifest(self.session, stream_url).items()
            return
        elif ".mp4" in stream_url:
            yield "vod", HTTPStream(self.session, stream_url)
            return

        for match in self._src_re.finditer(res.text):
            stream_url = match.group("url")
            if "\\/" in stream_url:
                # if the URL is json encoded, decode it
                stream_url = parse_json("\"{}\"".format(stream_url))
            if ".mpd" in stream_url:
                yield from DASHStream.parse_manifest(self.session, stream_url).items()
            elif ".mp4" in stream_url:
                yield match.group(1), HTTPStream(self.session, stream_url)
            else:
                log.debug("Non-dash/mp4 stream: {0}".format(stream_url))

        match = self._dash_manifest_re.search(res.text)
        if match:
            # facebook replaces "<" characters with the substring "\\x3C"
            manifest = match.group("manifest").replace("\\/", "/")
            manifest = bytes(unquote_plus(manifest), "utf-8").decode("unicode_escape")
            # Ignore unsupported manifests until DASH SegmentBase support is implemented
            if "SegmentBase" in manifest:
                log.error("Skipped DASH manifest with SegmentBase streams")
            else:
                yield from DASHStream.parse_manifest(self.session, manifest).items()

    def _get_streams(self):
        self.session.set_option("ffmpeg-start-at-zero", True)
        self.session.http.headers.update({"Accept-Language": "en-US"})

        done = False
        res = self.session.http.get(self.url)
        log.trace(f"{res.url}")

        title, canonical, self.title = validate.Schema(
            validate.parse_html(),
            validate.union((
                validate.xml_xpath_string(".//head/title[1]/text()"),
                validate.xml_xpath_string(".//head/meta[@res='canonical'][@href][1]/@href"),
                validate.xml_xpath_string(".//head/meta[@property='og:title'][@content][1]/@content"),
            ))
        ).validate(res.text)
        if canonical == "https://www.facebook.com/login/" or "log in" in title.lower():
            log.error("This URL requires a login or may be accessible from a different IP address.")
            return

        for s in self._parse_streams(res):
            done = True
            yield s
        if done:
            return

        # fallback on to playlist
        log.debug("Falling back to playlist regex")
        match = self._playlist_re.search(res.text)
        playlist = match and match.group(1)
        if playlist:
            match = self._plurl_re.search(playlist)
            if match:
                url = match.group(1)
                yield "sd", HTTPStream(self.session, url)
                return

        # fallback to tahoe player url
        log.debug("Falling back to tahoe player")
        video_id = self.match.group("video_id")
        url = self._TAHOE_URL.format(video_id)
        data = {
            "__a": 1,
            "__pc": self._DEFAULT_PC,
            "__rev": self._DEFAULT_REV,
            "fb_dtsg": "",
        }
        match = self._pc_re.search(res.text)
        if match:
            data["__pc"] = match.group(1)
        match = self._rev_re.search(res.text)
        if match:
            data["__rev"] = match.group(1)
        match = self._dtsg_re.search(res.text)
        if match:
            data["fb_dtsg"] = match.group(1)
        res = self.session.http.post(
            url,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=urlencode(data).encode("ascii")
        )

        yield from self._parse_streams(res)


__plugin__ = Facebook
