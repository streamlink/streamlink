#!/usr/bin/env python
import re
from pprint import pprint

from streamlink.plugin import Plugin
from streamlink.plugin.api import http, validate
from streamlink.stream import HLSStream
from streamlink.utils import parse_json


class AdultSwim(Plugin):
    _user_agent = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_3) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/43.0.2357.65 Safari/537.36")
    API_URL = "http://www.adultswim.com/videos/api/v2/videos/{id}?fields=stream"

    _url_re = re.compile(r"http://www\.adultswim\.com/videos/streams/(.*)")
    _stream_data_re = re.compile(r".*AS_INITIAL_DATA = (\{.*?});.*", re.M | re.DOTALL)

    _page_data_schema = validate.Schema({
        u"streams": {
            validate.text: {
                u"stream": validate.text
            }
        }
    })

    _api_schema = validate.Schema({
        u'status': u'ok',
        u'data': {
            u'stream': {
                u'assets': [
                    {
                        u'url': validate.url()
                    }
                ]
            }
        }
    })

    @classmethod
    def can_handle_url(cls, url):
        match = AdultSwim._url_re.match(url)
        return match is not None

    def _get_streams(self):
        # get the page
        res = http.get(self.url, headers={"User-Agent": self._user_agent})
        # find the big blob of stream info in the page
        stream_data = self._stream_data_re.match(res.text)
        stream_name = AdultSwim._url_re.match(self.url).group(1) or "live-stream"

        if stream_data:
            # parse the stream info as json
            stream_info = parse_json(stream_data.group(1), schema=self._page_data_schema)
            # get the stream ID
            stream_id = stream_info[u"streams"][stream_name][u"stream"]

            if stream_id:
                api_url = self.API_URL.format(id=stream_id)

                res = http.get(api_url, headers={"User-Agent": self._user_agent})
                stream_data = http.json(res, schema=self._api_schema)

                for asset in stream_data[u'data'][u'stream'][u'assets']:
                    for n, s in HLSStream.parse_variant_playlist(self.session, asset[u"url"]).items():
                        yield n, s

            else:
                self.logger.error("Couldn't find the stream ID for this stream: {}".format(stream_name))
        else:
            self.logger.error("Couldn't find the stream data for this stream: {}".format(stream_name))

__plugin__ = AdultSwim
