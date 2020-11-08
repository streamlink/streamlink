import logging
import re
from urllib.parse import urljoin

from streamlink.plugin import Plugin, PluginArgument, PluginArguments
from streamlink.plugin.api import validate
from streamlink.stream import DASHStream, HTTPStream
from streamlink.stream.ffmpegmux import MuxedStream

log = logging.getLogger(__name__)


class SVTPlay(Plugin):
    api_url = 'https://api.svt.se/videoplayer-api/video/{0}'

    author = None
    category = None
    title = None

    url_re = re.compile(r'''
        https?://(?:www\.)?(?:svtplay|oppetarkiv)\.se
        (/(kanaler/)?.*)
    ''', re.VERBOSE)

    latest_episode_url_re = re.compile(r'''
        class="play_titlepage__latest-video"\s+href="(?P<url>[^"]+)"
    ''', re.VERBOSE)

    live_id_re = re.compile(r'.*/(?P<live_id>[^?]+)')

    vod_id_re = re.compile(r'''
        (?:DATA_LAKE\s+=\s+{"content":{"id":|"svtId":|data-video-id=)
        "(?P<vod_id>[^"]+)"
    ''', re.VERBOSE)

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

    arguments = PluginArguments(
        PluginArgument("mux-subtitles", is_global=True)
    )

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def get_author(self):
        if self.author is not None:
            return self.author

    def get_category(self):
        if self.category is not None:
            return self.category

    def get_title(self):
        if self.title is not None:
            return self.title

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
        res = self.session.http.get(self.url)
        match = self.latest_episode_url_re.search(res.text)
        if match:
            res = self.session.http.get(
                urljoin(self.url, match.group('url')),
            )

        match = self.vod_id_re.search(res.text)
        if match is None:
            return

        vod_id = match.group('vod_id')
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

    def _get_streams(self):
        path, live = self.url_re.match(self.url).groups()
        log.debug("Path={0}".format(path))

        if live:
            return self._get_live(path)
        else:
            return self._get_vod()


__plugin__ = SVTPlay
