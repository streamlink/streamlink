"""Plugin for NPO: Nederlandse Publieke Omroep

Supports:
   VODs: http://www.npo.nl/het-zandkasteel/POMS_S_NTR_059963
   Live: http://www.npo.nl/live/nederland-1
"""

import re
import json

from streamlink.compat import quote
from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.stream import HTTPStream, HLSStream

_url_re = re.compile("http(s)?://(\w+\.)?npo.nl/")
HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1944.9 Safari/537.36"
}

class NPO(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def get_token(self):
        url = 'http://ida.omroep.nl/npoplayer/i.js?s={}'.format(quote(self.url))
        token = http.get(url, headers=HTTP_HEADERS).text
        token = re.compile('token.*?"(.*?)"', re.DOTALL + re.IGNORECASE).search(token).group(1)

        # Great the have a ['en','ok','t'].reverse() decurity option in npoplayer.js
        secured = list(token)
        token = list(token)

        first = -1
        second = -1
        for i, c in enumerate(token):
            if c.isdigit() and 4 < i < len(token):
                if first == -1:
                    first = i
                else:
                    second = i
                    break

        if first == -1:
            first = 12
        if second == -1:
            second = 13

        secured[first] = token[second]
        secured[second] = token[first]
        return ''.join(secured)

    def _get_meta(self):
        html = http.get('http://www.npo.nl/live/{}'.format(self.npo_id), headers=HTTP_HEADERS).text
        program_id = re.compile('data-prid="(.*?)"', re.DOTALL + re.IGNORECASE).search(html).group(1)
        meta = http.get('http://e.omroep.nl/metadata/{}'.format(program_id), headers=HTTP_HEADERS).text
        meta = re.compile('({.*})', re.DOTALL + re.IGNORECASE).search(meta).group(1)
        return json.loads(meta)

    def _get_vod_streams(self):
        url = 'http://ida.omroep.nl/odi/?prid={}&puboptions=adaptive,h264_bb,h264_sb,h264_std&adaptive=no&part=1&token={}'\
            .format(quote(self.npo_id), quote(self.get_token()))
        res = http.get(url, headers=HTTP_HEADERS);

        data = res.json()

        streams = {}
        stream = http.get(data['streams'][0].replace('jsonp', 'json'), headers=HTTP_HEADERS).json()
        streams['best'] = streams['high'] = HTTPStream(self.session, stream['url'])
        return streams

    def _get_live_streams(self):
        meta = self._get_meta()
        stream = [x for x in meta['streams'] if x['type'] == 'hls'][0]['url']

        url = 'http://ida.omroep.nl/aapi/?type=jsonp&stream={}&token={}'.format(stream, self.get_token())
        streamdata = http.get(url, headers=HTTP_HEADERS).json()
        deeplink = http.get(streamdata['stream'], headers=HTTP_HEADERS).text
        deeplink = re.compile('"(.*?)"', re.DOTALL + re.IGNORECASE).search(deeplink).group(1)
        playlist_url = deeplink.replace("\\/", "/")
        return HLSStream.parse_variant_playlist(self.session, playlist_url)

    def _get_streams(self):
        urlparts = self.url.split('/')
        self.npo_id = urlparts[-1]

        if (urlparts[-2] == 'live'):
            return self._get_live_streams()
        else:
            return self._get_vod_streams()

__plugin__ = NPO
