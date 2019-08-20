import re
from streamlink.plugin import Plugin
from streamlink.plugin.api import useragents
from streamlink.stream import HLSStream

_url_re = re.compile(r'https?://(www\.)?arconaitv\.us/stream\.php\?id=((\d+)|(random))')
_js_re = re.compile( r'.*eval\(function\(.*')
_data_re = re.compile('\|')

class ArconaiTv(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def _get_streams(self):
        headers = {
            'User-Agent': useragents.CHROME,
            'Referer': self.url
        }

        response = self.session.http.get(self.url, headers=headers)
        text = response.text
        search = _js_re.search(text)
        if search:
            data = _data_re.split(search.group(0))
        else:
            self.logger.error('No search, text: {0}'.format(
                text.encode('ascii', 'replace')))
            return
        url = '{0}://{1}.{2}/{3}/{4}/{5}/{6}.{7}'.format(data[14],
            data[27].strip("'.split('"), data[23], data[16], data[25],
            data[26], data[22], data[21])
        self.logger.debug('HLS URL: {0}'.format(url))
        yield 'live', HLSStream(self.session, url, headers=headers)

__plugin__ = ArconaiTv
