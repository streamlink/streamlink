"""Streamlink plugin for bongacams.com"""

import json
import re
import requests
import time

from io import BytesIO
from hashlib import md5
from urllib.parse import urljoin, urlsplit

from streamlink.exceptions import PluginError, NoStreamsError
from streamlink.packages.flashmedia.types import AMF0Value
from streamlink.packages.flashmedia import AMFPacket, AMFMessage
from streamlink.plugin.api import validate
from streamlink.plugin import Plugin
from streamlink.stream import RTMPStream
from streamlink.utils import parse_json


CONST_FLASH_VER = "WIN 24,0,0,186"
CONST_DEFAULT_SWF_LOCATION = '/swf/chat/BCamChat.swf?cache=20161226150'
CONST_AMF_GATEWAY_LOCATION = '/tools/amf.php'
CONST_AMF_GATEWAY_PARAM = 'x-country'

CONST_HEADERS = {}
CONST_HEADERS['User-Agent'] = 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) '
CONST_HEADERS['User-Agent'] += 'Chrome/54.0.2840.99 Safari/537.36 OPR/41.0.2353.69'

url_re = re.compile("^(https?://\w{2}.bongacams.com)/([\w\d_-]+)$")
swf_re = re.compile("/swf/\w+/\w+.swf\?cache=\d+")

amf_msg_schema = validate.Schema({
    "status" : "success",
    "userData" : {
        "username": validate.text
    },
    "localData" : {
        "NC_ConnUrl" : validate.url(scheme="rtmp"),
        "NC_AccessKey" : validate.length(32),
        "dataKey" : validate.length(32),
    },
    "performerData" : {
        "username" : validate.text,
    }
})


class AMFMessage2(AMFMessage):
    @property
    def size(self):
        size = AMF0Value.size(self.value)
        return size


class bongacams(Plugin):
    @classmethod
    def can_handle_url(self, url):
        return url_re.match(url)

    def _get_stream_uid(self, username):
        m = md5(username.encode('utf-8') + str(time.time()).encode('utf-8'))
        return m.hexdigest()

    def _get_streams(self):
        match = url_re.match(self.url)

        baseurl = match.group(1)
        chathost = match.group(2)
        chathost_url = match.group()
        amf_gateway_url = urljoin(baseurl, CONST_AMF_GATEWAY_LOCATION)
        country = urlsplit(baseurl).netloc[:2].lower()

        # create http session and set headers
        http_session = requests.Session()
        http_session.headers.update(CONST_HEADERS)

        # get swf url and cookies for next request
        r = http_session.get(chathost_url, allow_redirects=False)

        if r.is_redirect:
            self.logger.debug("redirect to: {}", r.headers.get('Location'))
            raise NoStreamsError
        if not r.ok:
            self.logger.debug("Status code for {}: {}", r.url, r.status_code)
            raise NoStreamsError
        if len(http_session.cookies) == 0:
            raise PluginError("Can't get a cookies")

        match = swf_re.search(r.text)
        if match:
            swf_url = urljoin(baseurl, match.group())
            self.logger.debug("swf url found: {}", swf_url)
        else:
            swf_url = urljoin(baseurl, CONST_DEFAULT_SWF_LOCATION)
            self.logger.debug("swf url not found. Will try {}", swf_url)

        # create amf query
        amf_message = AMFMessage2("svDirectAmf.getRoomData", "/1", [chathost, True])
        amf_packet = AMFPacket(version=0)
        amf_packet.messages.append(amf_message)

        # send request and close http-session
        r = http_session.post(url=amf_gateway_url,
                              params={CONST_AMF_GATEWAY_PARAM : country},
                              data=bytes(amf_packet.serialize()))
        http_session.close()

        if r.status_code != 200:
            raise PluginError("unexpected status code for {}: {}", r.url, r.status_code)

        amf_response = AMFPacket.deserialize(BytesIO(r.content))

        if len(amf_response.messages) != 1 or amf_response.messages[0].target_uri != "/1/onResult":
            raise PluginError("unexpected response from amf gate")

        stream_source_info = parse_json(json.dumps(amf_response.messages[0].value), schema=amf_msg_schema)
        self.logger.debug("source stream info:\n{}", stream_source_info)

        stream_params = {
            "live": True,
            "realtime": True,
            "verbose": True,
            "flashVer": CONST_FLASH_VER,
            "swfUrl": swf_url,
            "tcUrl": stream_source_info['localData']['NC_ConnUrl'],
            "rtmp": stream_source_info['localData']['NC_ConnUrl'],
            "pageUrl": chathost_url,
            "playpath": "%s?uid=%s" % (''.join(('stream_', chathost)),
                                       self._get_stream_uid(stream_source_info['userData']['username'])),
            # Multiple args with same name not supported.
            # Details: https://github.com/streamlink/streamlink/issues/321
            "conn" : "S:{username} --conn=S:{access_key} --conn=B:0 --conn=S:{data_key}".format(
                username=stream_source_info['userData']['username'],
                access_key=stream_source_info['localData']['NC_AccessKey'],
                data_key=stream_source_info['localData']['dataKey']
            )
        }

        self.logger.debug("Stream params:\n{}", stream_params)
        stream = RTMPStream(self.session, stream_params)

        return {'best': stream, 'high': stream}

__plugin__ = bongacams
