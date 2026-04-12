"""
$description Video hosting platform based on XFileSharing.
$url darkibox.com
$type vod
"""

import re

from streamlink.logger import getLogger
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.stream.hls import HLSStream
from streamlink.stream.http import HTTPStream


log = getLogger(__name__)


def _unpack(packed):
    """Unpack Dean Edwards packed JavaScript."""

    match = re.search(
        r"eval\(function\(p,a,c,k,e,[dr]\)\{.*?\}\('(.+?)',\s*(\d+),\s*(\d+),\s*'([^']+)'\.split\('\|'\)",
        packed,
    )
    if not match:
        return None

    payload, radix, count, keywords = match.groups()
    radix = int(radix)
    count = int(count)
    keywords = keywords.split("|")

    def _int_base_n(word, base):
        """Convert a base-N encoded string to an integer."""
        digits = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        result = 0
        for char in word:
            result = result * base + digits.index(char)
        return result

    def _lookup(match):
        word = match.group(0)
        try:
            idx = _int_base_n(word, radix)
        except ValueError:
            return word
        if idx < len(keywords) and keywords[idx]:
            return keywords[idx]
        return word

    result = re.sub(r"\b\w+\b", _lookup, payload)
    return result


@pluginmatcher(
    re.compile(r"https?://(?:www\.)?darkibox\.com/(?:embed-|d/)?(?P<filecode>[a-zA-Z0-9]+)"),
)
class Darkibox(Plugin):
    EMBED_URL = "https://darkibox.com/embed-{filecode}.html"
    DL_URL = "https://darkibox.com/dl"

    def _get_streams(self):
        filecode = self.match.group("filecode")
        # Strip .html suffix if captured
        filecode = re.sub(r"\.html$", "", filecode)
        log.debug(f"File code: {filecode}")

        res = self.session.http.post(
            self.DL_URL,
            data={
                "op": "embed",
                "file_code": filecode,
                "auto": "1",
            },
            headers={
                "Referer": self.EMBED_URL.format(filecode=filecode),
            },
        )

        unpacked = _unpack(res.text)
        if not unpacked:
            log.error("Could not unpack player response")
            return

        log.trace(f"Unpacked JS: {unpacked}")

        # Try to find the video URL from PlayerJS file:"URL" parameter
        m = re.search(r'file\s*:\s*"([^"]+)"', unpacked)
        if not m:
            log.error("Could not find video URL in unpacked response")
            return

        video_url = m.group(1)
        log.debug(f"Video URL: {video_url}")

        # Handle multi-quality format: [label]url,[label]url,...
        if video_url.startswith("["):
            for match in re.finditer(r"\[([^\]]+)\]([^,\s\[]+)", video_url):
                label, url = match.groups()
                if ".m3u8" in url:
                    streams = HLSStream.parse_variant_playlist(self.session, url, headers={"Referer": self.EMBED_URL.format(filecode=filecode)})
                    if streams:
                        yield from streams.items()
                    else:
                        yield label, HLSStream(self.session, url, headers={"Referer": self.EMBED_URL.format(filecode=filecode)})
                else:
                    yield label, HTTPStream(self.session, url, headers={"Referer": self.EMBED_URL.format(filecode=filecode)})
        elif ".m3u8" in video_url:
            return HLSStream.parse_variant_playlist(self.session, video_url, headers={"Referer": self.EMBED_URL.format(filecode=filecode)})
        else:
            return {"video": HTTPStream(self.session, video_url, headers={"Referer": self.EMBED_URL.format(filecode=filecode)})}


__plugin__ = Darkibox
