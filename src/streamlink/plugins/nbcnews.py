import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream
from streamlink.utils import parse_json


class NBCNews(Plugin):
    url_re = re.compile(r'https?://(www.)?nbcnews.com/now')
    js_re = re.compile(r'https://ndassets.s-nbcnews.com/main-[0-9a-f]{20}.js')
    api_re = re.compile(r'NEWS_NOW_PID="([0-9]+)"')
    api_url = 'https://stream.nbcnews.com/data/live_sources_{0}.json'
    api_schema = validate.Schema(validate.transform(parse_json), {
        "videoSources": [{
            "sourceUrl": validate.url()
        }]
    }, validate.get("videoSources"), validate.get(0), validate.get("sourceUrl"))

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        html = self.session.http.get(self.url).text
        match = self.js_re.search(html)
        js = self.session.http.get(match[0]).text
        match = self.api_re.search(js)
        api_url = self.api_url.format(match[1])
        stream_url = self.session.http.get(api_url, schema=self.api_schema)
        return HLSStream.parse_variant_playlist(self.session, stream_url)


__plugin__ = NBCNews
