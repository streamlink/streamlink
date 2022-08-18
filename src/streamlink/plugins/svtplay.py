"""
$description Live TV channels and video on-demand service from SVT, a Swedish public, state-owned broadcaster.
$url svtplay.se
$type live, vod
$region Sweden
"""

import logging
import re
from urllib.parse import parse_qsl, urlparse

from streamlink.plugin import Plugin, pluginargument, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.dash import DASHStream
from streamlink.stream.ffmpegmux import MuxedStream
from streamlink.stream.http import HTTPStream

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r'https?://(?:www\.)?svtplay\.se(/(kanaler/)?.*)'
))
@pluginargument(
    "mux-subtitles",
    is_global=True,
)
class SVTPlay(Plugin):
    api_url = 'https://api.svt.se/videoplayer-api/video/{0}'

    latest_episode_url_re = re.compile(r'''
        data-rt="top-area-play-button"\s+href="(?P<url>[^"]+)"
    ''', re.VERBOSE)

    live_id_re = re.compile(r'.*/(?P<live_id>[^?]+)')

    _video_schema = validate.Schema({
        validate.optional('programTitle'): validate.text,
        validate.optional('episodeTitle'): validate.text,
        'videoReferences': [{
            'url': validate.url(),
            'format': validate.text,
        }],
        validate.optional('subtitleReferences'): [{
            'url': validate.url(),
            'format': validate.text,
        }],
    })

    def _set_metadata(self, data, category):
        if 'programTitle' in data:
            self.author = data['programTitle']

        self.category = category

        if 'episodeTitle' in data:
            self.title = data['episodeTitle']

    def _get_live(self, path):
        match = self.live_id_re.search(path)
        if match is None:
            return

        live_id = "ch-{0}".format(match.group('live_id'))
        log.debug("Live ID={0}".format(live_id))

        res = self.session.http.get(self.api_url.format(live_id))
        api_data = self.session.http.json(res, schema=self._video_schema)

        self._set_metadata(api_data, 'Live')

        for playlist in api_data['videoReferences']:
            if playlist['format'] == 'dashhbbtv':
                yield from DASHStream.parse_manifest(self.session, playlist['url']).items()

    def _get_vod(self):
        vod_id = self._get_vod_id(self.url)

        if vod_id is None:
            res = self.session.http.get(self.url)
            match = self.latest_episode_url_re.search(res.text)
            if match is None:
                return
            vod_id = self._get_vod_id(match.group("url"))

        if vod_id is None:
            return

        log.debug("VOD ID={0}".format(vod_id))

        res = self.session.http.get(self.api_url.format(vod_id))
        api_data = self.session.http.json(res, schema=self._video_schema)

        self._set_metadata(api_data, 'VOD')

        substreams = {}
        if 'subtitleReferences' in api_data:
            for subtitle in api_data['subtitleReferences']:
                if subtitle['format'] == 'webvtt':
                    log.debug("Subtitle={0}".format(subtitle['url']))
                    substreams[subtitle['format']] = HTTPStream(
                        self.session,
                        subtitle['url'],
                    )

        for manifest in api_data['videoReferences']:
            if manifest['format'] == 'dashhbbtv':
                for q, s in DASHStream.parse_manifest(self.session, manifest['url']).items():
                    if self.get_option('mux_subtitles') and substreams:
                        yield q, MuxedStream(self.session, s, subtitles=substreams)
                    else:
                        yield q, s

    def _get_vod_id(self, url):
        qs = dict(parse_qsl(urlparse(url).query))
        return qs.get("id")

    def _get_streams(self):
        path, live = self.match.groups()
        log.debug("Path={0}".format(path))

        if live:
            return self._get_live(path)
        else:
            return self._get_vod()


__plugin__ = SVTPlay
