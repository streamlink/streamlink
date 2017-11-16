import json
import re

from streamlink.compat import urljoin, urlparse, urlunparse
from streamlink.exceptions import PluginError, NoStreamsError
from streamlink.plugin.api import validate, http, useragents
from streamlink.plugin import Plugin
from streamlink.stream import HLSStream
from streamlink.utils import update_scheme

CONST_AMF_GATEWAY_LOCATION = '/tools/amf.php'
CONST_AMF_GATEWAY_PARAM = 'x-country'
CONST_DEFAULT_COUNTRY_CODE = 'en'

CONST_HEADERS = {}
CONST_HEADERS['User-Agent'] = useragents.CHROME

url_re = re.compile(r"(http(s)?://)?(\w{2}.)?(bongacams\.com)/([\w\d_-]+)")

amf_msg_schema = validate.Schema({
    "status": "success",
    "userData": {
        "username": validate.text
    },
    "localData": {
        "videoServerUrl": validate.text
    },
    "performerData": {
        "username": validate.text,
    }
})


class bongacams(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return url_re.match(url)

    def _get_streams(self):
        match = url_re.match(self.url)

        stream_page_scheme = 'https'
        stream_page_domain = match.group(4)
        stream_page_path = match.group(5)
        country_code = CONST_DEFAULT_COUNTRY_CODE

        # create http session and set headers
        http_session = http
        http_session.headers.update(CONST_HEADERS)

        # get cookies
        r = http_session.get(urlunparse((stream_page_scheme, stream_page_domain, stream_page_path, '', '', '')))

        # redirect to profile page means stream is offline
        if '/profile/' in r.url:
            raise NoStreamsError(self.url)
        if not r.ok:
            self.logger.debug("Status code for {0}: {1}", r.url, r.status_code)
            raise NoStreamsError(self.url)
        if len(http_session.cookies) == 0:
            raise PluginError("Can't get a cookies")

        if urlparse(r.url).netloc != stream_page_domain:
            # then redirected to regional subdomain
            country_code = urlparse(r.url).netloc.split('.')[0].lower()

        # time to set variables
        baseurl = urlunparse((stream_page_scheme, urlparse(r.url).netloc, '', '', '', ''))
        amf_gateway_url = urljoin(baseurl, CONST_AMF_GATEWAY_LOCATION)
        stream_page_url = urljoin(baseurl, stream_page_path)

        headers = {
            'User-Agent': useragents.CHROME,
            'Referer': stream_page_url,
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest'
        }

        data = 'method=getRoomData&args%5B%5D={0}&args%5B%5D=false'.format(stream_page_path)
        self.logger.debug('DATA: {0}'.format(str(data)))
        # send request and close http-session
        r = http_session.post(url=amf_gateway_url,
                              headers=headers,
                              params={CONST_AMF_GATEWAY_PARAM: country_code},
                              data=data)
        http_session.close()

        if r.status_code != 200:
            raise PluginError("unexpected status code for {0}: {1}", r.url, r.status_code)

        stream_source_info = amf_msg_schema.validate(json.loads(r.text))
        self.logger.debug("source stream info:\n{0}", stream_source_info)

        if not stream_source_info:
            return

        urlnoproto = stream_source_info['localData']['videoServerUrl']
        urlnoproto = update_scheme('https://', urlnoproto)
        performer = stream_source_info['performerData']['username']

        hls_url = '{0}/hls/stream_{1}/playlist.m3u8'.format(urlnoproto, performer)

        if hls_url:
            self.logger.debug('HLS URL: {0}'.format(hls_url))
            try:
                for s in HLSStream.parse_variant_playlist(self.session, hls_url, headers=headers).items():
                    yield s
            except Exception as e:
                if '404' in str(e):
                    self.logger.error('Stream is currently offline or private')
                else:
                    self.logger.error(str(e))
                return


__plugin__ = bongacams
