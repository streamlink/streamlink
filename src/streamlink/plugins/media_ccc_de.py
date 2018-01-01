"""Plugin for media.ccc.de

Media.ccc.de is a distribution platform for multimedia files provided by the
Chaos Computer Club. It provides a wide variety of video and audio material
in native formats.

Some CCC related events like the Chaos Communication Congress are live
streamed on streaming.media.ccc.de.

Supports:
    - http://media.ccc.de (vod)
    - http://streaming.media.ccc.de (livestreaming)

Limitations:
    * streaming.media.ccc.de:
        - only HLS and audio only (opus and mp3) live streams are supported

    * media.ccc.de
        - only mp4 and audio only (opus and mp3) recordings are supported
"""

import re

from streamlink.plugin import Plugin, PluginError
from streamlink.plugin.api import http
from streamlink.stream import HTTPStream, HLSStream

API_URL_MEDIA = "https://api.media.ccc.de"
API_URL_STREAMING_MEDIA = "https://streaming.media.ccc.de/streams/v1.json"

# http(s)://media.ccc.de/path/to/talk.html
_url_media_re = re.compile(r"(?P<scheme>http|https)"
                           r"://"
                           r"(?P<server>media\.ccc\.de)"
                           r"/")
# https://streaming.media.ccc.de/room/
_url_streaming_media_re = re.compile(r"(?P<scheme>http|https)"
                                     r"://"
                                     r"(?P<server>streaming\.media\.ccc\.de)"
                                     r"/"
                                     r"(?P<room>.*)"
                                     r"/")


def get_event_id(url):
    """Extract event id from talk html page.

    Raises :exc:`PluginError` on failure.

    :param url: talk URL

    """
    match = re.search(r"{event_id:\s(?P<event_id>\d+),.*}", http.get(url).text)

    try:
        event_id = int(match.group('event_id'))
    except Exception:
        raise PluginError("Failed to get event id from URL.")

    return event_id


def get_json(url):
    """Fetch page for given URL and return json Python object.

    :param url: URL to fetch

    """
    res = http.get(url)

    return http.json(res)


def parse_media_json(json_object):
    """Expose available file formats.

    :param json_string: json as string

    """
    recordings = {}
    for recording in json_object['recordings']:
        match = re.search(r".*\/(?P<format>.*)", recording['mime_type'])
        file_format = match.group('format')

        if recording['mime_type'] == 'vnd.voc/mp4-web' or\
                recording['display_mime_type'] == 'video/webm':
            continue
        elif recording['mime_type'] == 'vnd.voc/h264-hd':
            name = "1080p"
        elif recording['mime_type'] == 'vnd.voc/h264-lq':
            name = "420p"
        elif re.match(r"audio", recording['display_mime_type']):
            name = "audio_%s" % file_format
        else:
            if recording['hd'] == 'True':
                name = "1080p"
            else:
                name = "420p"

        recordings[name] = recording['recording_url']

    return recordings


def parse_streaming_media_json(json_object, room_from_url):
    """Filter all available live streams for given json and room name.

    API-Doku: https://github.com/voc/streaming-website#json-api

    :param json_string: json as string
    :param room_from_url:

    """
    streams = {}
    for group in json_object:
        for room in group['rooms']:
            # only consider to requested room
            match = _url_streaming_media_re.match(room['link'])
            if not match.group('room') == room_from_url:
                continue

            for stream in room['streams']:
                # get stream language
                if stream['isTranslated'] is False:
                    language = 'native'
                else:
                    language = 'translated'

                # get available hls stream urls
                hls_stream = stream['urls'].get('hls')
                if hls_stream:
                    stream_url = hls_stream['url']
                    name = None
                    # native HLS streams are announced as
                    # ${height}p and (hd|sd)_native_${height}p
                    if language == 'native':
                        name = "%sp" % stream['videoSize'][-1]
                        long_name = "hls_%s_%sp" % ("native",
                                                    stream['videoSize'][-1])
                        streams[name] = stream_url
                        streams[long_name] = stream_url
                    elif language == 'translated':
                        long_name = "hls_%s_%sp" % ("translated",
                                                    stream['videoSize'][-1])
                        streams[long_name] = stream_url

                # get available audio only mpeg urls
                mp3_stream = stream['urls'].get('mp3')
                if mp3_stream:
                    stream_url = mp3_stream['url']
                    name = "audio_%s_mpeg" % language
                    streams[name] = stream_url

                # get available audio only opus urls
                opus_stream = stream['urls'].get('opus')
                if opus_stream:
                    stream_url = opus_stream['url']
                    name = "audio_%s_opus" % language
                    streams[name] = stream_url

    return streams


class media_ccc_de(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return _url_media_re.match(url) or _url_streaming_media_re.match(url)

    def _get_streams(self):
        streams = {}

        # streaming.media.ccc.de
        match = _url_streaming_media_re.match(self.url)
        if match:
            query_url = API_URL_STREAMING_MEDIA
            live_streams = parse_streaming_media_json(get_json(query_url),
                                                      match.group('room'))

            for stream_name, stream_url in live_streams.items():
                if re.search(r"m3u8", live_streams[stream_name]):
                    streams[stream_name] = HLSStream(self.session,
                                                     stream_url)
                else:
                    streams[stream_name] = HTTPStream(self.session,
                                                      stream_url)

        # media.ccc.de
        elif _url_media_re.search(self.url):
            event_id = get_event_id(self.url)
            query_url = "%s/public/events/%i" % (API_URL_MEDIA, event_id)
            recordings = parse_media_json(get_json(query_url))

            for name, stream_url in recordings.items():
                streams[name] = HTTPStream(self.session, stream_url)

        if not streams:
            raise PluginError("This plugin does not support your "
                              "selected video.")

        return streams


__plugin__ = media_ccc_de
