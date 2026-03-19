"""YouTube plugin for Streamlink.

Supported URL formats:
  youtube.com/watch?v=VIDEO_ID  youtube.com/v/VIDEO_ID  youtube.com/live/VIDEO_ID
  youtu.be/VIDEO_ID             youtube.com/embed/VIDEO_ID
  youtube.com/@channel/live     gaming.youtube.com/...
"""

import logging
import re
from urllib.parse import urlparse

from streamlink.plugin import Plugin, pluginmatcher, pluginargument
from streamlink.stream.hls import HLSStream
from .deno import DenoJCP
from .structures import Extractor, ExtractorResult, ctx, StreamPick
from .extractors import VideoExtractor, LiveExtractor, StreamsExtractor
from .youtube import YouTube as YtOriginal

log = logging.getLogger(__name__)


@pluginmatcher(
    name="default",
    pattern=re.compile(
        r"https?://(?:\w+\.)?youtube\.com/(?:v/|live/|watch\?(?:.*&)?v=)(?P<video_id>[\w-]{11})",
    ),
)
@pluginmatcher(
    name="channel",
    pattern=re.compile(
        r"https?://(?:\w+\.)?youtube\.com/(?:@|c(?:hannel)?/|user/)?(?P<channel>[^/?]+)(?P<tab>/(?:live|streams))?/?$",
    ),
)
@pluginmatcher(
    name="embed",
    pattern=re.compile(
        r"https?://(?:\w+\.)?youtube\.com/embed/(?:live_stream\?channel=(?P<live>[^/?&]+)|(?P<video_id>[\w-]{11}))",
    ),
)
@pluginmatcher(
    name="shorthand",
    pattern=re.compile(
        r"https?://youtu\.be/(?P<video_id>[\w-]{11})",
    ),
)
@pluginargument(
    "stream",
    default="popular",
    metavar=StreamPick.metavar(),
    help="""
        Select which stream to play when opening a channel page or /streams listing.
        Can be `first`, `last`, `popular`, or a position number of the active stream (e.g. `1`, `2`, `3`).
        Defaults to `popular`.
    """,
)
class Youtube(Plugin):
    """Streamlink plugin for YouTube. Resolves live and VOD streams via an extractor chain."""

    _EXTRACTORS: list[type[Extractor]] = [VideoExtractor, LiveExtractor, StreamsExtractor]

    _url_canonical: str = "https://www.youtube.com/watch?v={video_id}"
    _url_channelid_live: str = "https://www.youtube.com/channel/{channel_id}/live"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.url = self._normalize_url()
        log.debug(f"Normalized URL: {self.url}")
        ctx.session = self.session
        ctx.options = self.options
        ctx.deno = DenoJCP()

    def _normalize_url(self) -> str:
        """Normalize various YouTube URL formats to a canonical HTTPS URL."""
        parsed = urlparse(self.url)

        if parsed.netloc == "gaming.youtube.com":
            return parsed._replace(scheme="https", netloc="www.youtube.com").geturl()
        elif self.matches["shorthand"]:
            return self._url_canonical.format(video_id=self.match["video_id"])
        elif self.matches["embed"] and self.match["video_id"]:
            return self._url_canonical.format(video_id=self.match["video_id"])
        elif self.matches["embed"] and self.match["live"]:
            return self._url_channelid_live.format(channel_id=self.match["live"])
        elif self.matches["channel"] and not self.match["tab"]:
            return self.url.rstrip("/") + "/streams"
        elif parsed.scheme != "https":
            return parsed._replace(scheme="https").geturl()
        return self.url

    def _next_extract(self, prev_result: ExtractorResult = None):
        """Recursively extract stream data through extractor chain.

        YouTube extraction may require multiple steps:
        1. TabExtractor: Channel/live pages -> video URL
        2. VideoExtractor: Video page -> HLS manifest URLs

        Args:
            prev_result: Result from previous extraction step

        Returns:
            list[str]: HLS manifest URLs
        """
        if not prev_result:
            extractor = next((e for e in self._EXTRACTORS if re.match(e.valid_url_re, self.url)), None)
            url = self.url
        elif prev_result.hls:
            log.debug(f"Resolved {len(prev_result.hls)} HLS manifest(s)")
            return prev_result.hls
        else:
            extractor = next((e for e in self._EXTRACTORS if e.extractor_type == prev_result.next.extractor))
            url = prev_result.next.url

        if not extractor:
            log.warning(f"No extractor found for URL: {self.url}")
            return []

        log.debug(f"Chaining to {extractor.__name__} for {url}")
        return self._next_extract(prev_result=extractor().extract(url))

    def _check_streams(self, urls):
        """Parse and probe HLS variant playlists, discarding unreachable streams.

        Args:
            urls: HLS manifest URLs to probe

        Returns:
            list[tuple[str, HLSStream]]: Stream quality name to HLS stream object mapping
        """
        streams = []
        for m3u8_url in urls:
            try:
                variant_playlist = HLSStream.parse_variant_playlist(self.session, m3u8_url)
                v = next(iter(variant_playlist.values()))
                with v.open() as fd:
                    fd.timeout = 2
                    fd.read(64)
                streams.extend(variant_playlist.items())
            except Exception as e:
                log.warning(f"Skipping unreachable stream {m3u8_url}: {e}")

        if not streams:
            raise ValueError("No playable streams returned by extractors")
        return streams

    def _get_streams(self):
        """Extract and yield HLS streams from YouTube.

        Yields:
            tuple[str, HLSStream]: Stream quality name and HLS stream object
        """

        try:
            # Extract HLS manifest URLs through extractor chain
            m3u8_urls = self._next_extract()
            yield from self._check_streams(m3u8_urls)

        except Exception as e:
            log.error(f"Extraction failed: {e}")
            log.info("Falling back to original YouTube plugin")
            self.url = self.url.removesuffix("/streams")
            yield from YtOriginal(self.session, self.url, self.options)._get_streams().items()
