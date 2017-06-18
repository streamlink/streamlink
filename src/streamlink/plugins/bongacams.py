import re
import time

from io import BytesIO
from hashlib import md5

from streamlink.compat import bytes, urljoin, urlparse, urlunparse
from streamlink.exceptions import PluginError, NoStreamsError
from streamlink.packages.flashmedia.types import AMF0String, AMF0Value, U32BE
from streamlink.packages.flashmedia import AMFPacket, AMFMessage
from streamlink.plugin.api import validate, http
from streamlink.plugin import Plugin
from streamlink.stream import RTMPStream


CONST_FLASH_VER = "WIN 24,0,0,186"
CONST_DEFAULT_SWF_LOCATION = '/swf/chat/BCamChat.swf?cache=20161226150'
CONST_AMF_GATEWAY_LOCATION = '/tools/amf.php'
CONST_AMF_GATEWAY_PARAM = 'x-country'
CONST_DEFAULT_COUNTRY_CODE = 'en'

CONST_HEADERS = {}
CONST_HEADERS['User-Agent'] = 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) '
CONST_HEADERS['User-Agent'] += 'Chrome/54.0.2840.99 Safari/537.36 OPR/41.0.2353.69'

url_re = re.compile(r"(http(s)?://)?(\w{2}.)?(bongacams.com)/([\w\d_-]+)")
swf_re = re.compile(r"/swf/\w+/\w+.swf\?cache=\d+")

amf_msg_schema = validate.Schema({
    "status": "success",
    "userData": {
        "username": validate.text
    },
    "localData": {
        "NC_ConnUrl": validate.url(scheme="rtmp"),
        "NC_AccessKey": validate.length(32),
        "dataKey": validate.length(32),
    },
    "performerData": {
        "username": validate.text,
    }
})


class bongacams(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return url_re.match(url)

    def _get_stream_uid(self, username):
        m = md5(username.encode('utf-8') + str(time.time()).encode('utf-8'))
        return m.hexdigest()

    def _get_streams(self):
        match = url_re.match(self.url)

        stream_page_scheme = 'https'
        stream_page_domain = match.group(4)
        stream_page_path = match.group(5)
        country_code = CONST_DEFAULT_COUNTRY_CODE
        is_paid_show = False

        # create http session and set headers
        http_session = http
        http_session.headers.update(CONST_HEADERS)

        # get swf url and cookies
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

        match = swf_re.search(r.text)
        if match:
            swf_url = urljoin(baseurl, match.group())
            self.logger.debug("swf url found: {0}", swf_url)
        else:
            # most likely it means that country/region banned
            # can try use default swf-url
            swf_url = urljoin(baseurl, CONST_DEFAULT_SWF_LOCATION)
            self.logger.debug("swf url not found. Will try {0}", swf_url)

        # create amf query
        amf_message = AMFMessage("svDirectAmf.getRoomData", "/1", [stream_page_path, is_paid_show])
        amf_packet = AMFPacket(version=0)
        amf_packet.messages.append(amf_message)

        # send request and close http-session
        r = http_session.post(url=amf_gateway_url,
                              params={CONST_AMF_GATEWAY_PARAM: country_code},
                              data=bytes(amf_packet.serialize()))
        http_session.close()

        if r.status_code != 200:
            raise PluginError("unexpected status code for {0}: {1}", r.url, r.status_code)

        amf_response = AMFPacket.deserialize(BytesIO(r.content))

        if len(amf_response.messages) != 1 or amf_response.messages[0].target_uri != "/1/onResult":
            raise PluginError("unexpected response from amf gate")

        stream_source_info = amf_msg_schema.validate(amf_response.messages[0].value)
        self.logger.debug("source stream info:\n{0}", stream_source_info)

        stream_params = {
            "live": True,
            "realtime": True,
            "flashVer": CONST_FLASH_VER,
            "swfUrl": swf_url,
            "tcUrl": stream_source_info['localData']['NC_ConnUrl'],
            "rtmp": stream_source_info['localData']['NC_ConnUrl'],
            "pageUrl": stream_page_url,
            "playpath": "%s?uid=%s" % (''.join(('stream_', stream_page_path)),
                                       self._get_stream_uid(stream_source_info['userData']['username'])),
            "conn": ["S:{0}".format(stream_source_info['userData']['username']),
                     "S:{0}".format(stream_source_info['localData']['NC_AccessKey']),
                     "B:0",
                     "S:{0}".format(stream_source_info['localData']['dataKey'])]
        }

        self.logger.debug("Stream params:\n{0}", stream_params)
        stream = RTMPStream(self.session, stream_params)

        return {'live': stream}


__plugin__ = bongacams
