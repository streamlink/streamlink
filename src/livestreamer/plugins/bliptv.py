import re

from livestreamer.plugin import Plugin, PluginError
from livestreamer.plugin.api import http
from livestreamer.stream import HTTPStream

_url_re = re.compile("(http(s)?://)?blip.tv/.*-(?P<videoid>\d+)")
VIDEO_GET_URL = 'http://player.blip.tv/file/get/{0}'
SINGLE_VIDEO_URL = '.*\.((mp4)|(mov)|(m4v)|(flv))'


def get_quality_dict(quality_list):
    quality_list.sort()
    quality_dict = {}
    i = 0
    for bitrate in quality_list:
        if i == 0:
            quality_dict['%i' % bitrate] = 'low'
        elif i == 1:
            quality_dict['%i' % bitrate] = 'medium'
        elif i == 2:
            quality_dict['%i' % bitrate] = 'high'
        elif i == 3:
            quality_dict['%i' % bitrate] = 'ultra'
        else:
            quality_dict['%i' % bitrate] = 'ultra+_%i' % (i-3)
        i += 1
    return quality_dict


class bliptv(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_streams(self):
        match = _url_re.match(self.url)
        videoid = match.group("videoid")
        try:
            get_return = http.get(VIDEO_GET_URL.format(videoid))
        except:
            raise PluginError('Can not get video information from blip.tv for id %s' % videoid)
        json_decode = http.json(get_return)
        streams = {}
        quality_list = []
        for stream in json_decode:
            if re.compile(SINGLE_VIDEO_URL).match(stream['direct_url']):
                quality_list.append(int(stream['video_bitrate']))
        if len(quality_list) == 0:
            raise PluginError('No videos on blip.tv found for id %s' % videoid)
        quality_dict = get_quality_dict(quality_list)
        for stream in json_decode:
            if re.compile(SINGLE_VIDEO_URL).match(stream['direct_url']):
                streams[quality_dict[stream['video_bitrate']]] = HTTPStream(self.session, stream['direct_url'])
        quality_list.sort()
        streams['worst'] = streams[quality_dict['%i' % quality_list[0]]]
        streams['best'] = streams[quality_dict['%i' % quality_list[-1]]]
        return streams

__plugin__ = bliptv
