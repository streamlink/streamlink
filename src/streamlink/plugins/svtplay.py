import logging
import re

from streamlink.compat import urljoin
from streamlink.exceptions import PluginError
from streamlink.plugin import Plugin, PluginArguments, PluginArgument
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
        https?://(?:www\.)?(?:svtplay|oppetarkiv).se(?P<path>.*)
    ''', re.VERBOSE)

    latest_episode_url_re = re.compile(r'''
        class="play_titlepage__latest-video"\s+href="(?P<url>[^"]+)"
    ''', re.VERBOSE)

    live_id_re = re.compile(r'.*/(?P<live_id>[^?]+)')

    vod_id_re = re.compile(r'''
        (?:DATA_LAKE\s+=\s+{"content":{"id":|data-video-id=)
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
        PluginArgument(
            'mux-subtitles',
            action='store_true',
            help="Automatically mux available subtitles in to the output stream.",
        ),
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

    def _get_streams(self):
        path = self.url_re.match(self.url).group('path')
        log.debug("Path={0}".format(path))

        if path.startswith('/kanaler/'):
            match = self.live_id_re.search(path)
            if match is not None:
                live_id = "ch-{0}".format(match.group('live_id'))
                log.debug("Live ID={0}".format(live_id))
            else:
                raise PluginError("Failed to get live ID")

            res = self.session.http.get(self.api_url.format(live_id))
            api_data = self.session.http.json(res, schema=self._video_schema)

            if 'programTitle' in api_data:
                self.author = api_data['programTitle']

            self.category = 'Live'

            if 'episodeTitle' in api_data:
                self.title = api_data['episodeTitle']

            for playlist in api_data['videoReferences']:
                if playlist['format'] == 'dashhbbtv':
                    for s in DASHStream.parse_manifest(self.session, playlist['url']).items():
                        yield s
        else:
            res = self.session.http.get(self.url)
            match = self.latest_episode_url_re.search(res.text)
            if match:
                res = self.session.http.get(
                    urljoin(self.url, match.group('url')),
                )

            match = self.vod_id_re.search(res.text)

            if match is not None:
                vod_id = match.group('vod_id')
                log.debug("VOD ID={0}".format(vod_id))
            else:
                raise PluginError("Failed to get VOD ID")

            res = self.session.http.get(self.api_url.format(vod_id))
            api_data = self.session.http.json(res, schema=self._video_schema)

            if 'programTitle' in api_data:
                self.author = api_data['programTitle']

            self.category = 'VOD'

            if 'episodeTitle' in api_data:
                self.title = api_data['episodeTitle']

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


__plugin__ = SVTPlay
