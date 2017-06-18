from __future__ import print_function
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.compat import urlparse, parse_qsl
from streamlink.plugin.api import useragents
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream
from streamlink.stream import RTMPStream
from streamlink.utils import parse_json


class TV8cat(Plugin):
    url_re = re.compile(r"https?://(?:www\.)?tv8\.cat/directe/?")
    live_iframe = "http://www.8tv.cat/wp-content/themes/8tv/_/inc/_live_html.php"
    iframe_re = re.compile(r'iframe .*?src="((?:https?)?//[^"]*?)"')
    account_id_re = re.compile(r"accountId:\"(\d+?)\"")
    policy_key_re = re.compile(r"policyKey:\"(.+?)\"")
    britecove = "https://edge.api.brightcove.com/playback/v1/accounts/{account_id}/videos/{video_id}"
    britecove_schema = validate.Schema({
        "sources": [
            {"height": int,
             validate.optional("src"): validate.url(),
             validate.optional("app_name"): validate.url(scheme="rtmp"),
             validate.optional("stream_name"): validate.text}
        ]
    })

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _find_iframe(self, res):
        iframe = self.iframe_re.search(res.text)
        url = iframe and iframe.group(1)
        if url and url.startswith("//"):
            p = urlparse(self.url)
            url = "{0}:{1}".format(p.scheme, url)
        return url

    def _britecove_params(self, url):
        res = http.get(url, headers={"User-Agent": useragents.FIREFOX,
                                     "Referer": self.url})
        acc = self.account_id_re.search(res.text)
        pk = self.policy_key_re.search(res.text)

        query = dict(parse_qsl(urlparse(url).query))
        return {"video_id": query.get("videoId"),
                "account_id": acc and acc.group(1),
                "policy_key": pk and pk.group(1),
                }

    def _get_stream_data(self, **params):
        api_url = self.britecove.format(**params)
        res = http.get(api_url, headers={"Accept": "application/json;pk={policy_key}".format(**params)})
        return parse_json(res.text, schema=self.britecove_schema)

    def _get_streams(self):
        res = http.get(self.live_iframe)
        britecove_url = self._find_iframe(res)

        if britecove_url:
            self.logger.debug("Found britecove embed url: {0}", britecove_url)
            params = self._britecove_params(britecove_url)
            self.logger.debug("Got britecode params: {0}", params)
            stream_info = self._get_stream_data(**params)
            for source in stream_info.get("sources"):
                if source.get("src"):
                    for s in HLSStream.parse_variant_playlist(self.session, source.get("src")).items():
                        yield s
                else:
                    q = "{0}p".format(source.get("height"))
                    s = RTMPStream(self.session,
                                   {"rtmp": source.get("app_name"),
                                    "playpath": source.get("stream_name")})
                    yield q, s


__plugin__ = TV8cat
