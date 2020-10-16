import logging
import re
import html
import json

from streamlink.plugin import Plugin
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)


class URPlay(Plugin):
    api_url = 'https://api.svt.se/videoplayer-api/video/{0}'

    author = None
    category = None
    title = None

    url_re = re.compile(r'https?://(?:www\.)?urplay\.se/program/.*', re.VERBOSE)

    data_re = re.compile(r'''
        data-react-class="components/Player/Player"\sdata-react-props="(?P<json>[^"]+)"
    ''', re.VERBOSE)

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def get_author(self):
        if self.author is not None:
            return self.author

    def get_category(self):
        if self.category is not None:
            return self.category

    def get_title(self):
        if self.title is not None:
            return self.title

    def _get_streams(self):
        res = self.session.http.get(self.url)
        match = self.data_re.search(res.text)

        obj = json.loads(html.unescape(match.group('json')))
        data = obj["currentProduct"]

        self.title = data["title"]
        self.author = data["mainTitle"]
        self.category = data["mainGenre"]

        for type in data["streamingInfo"]["raw"]:

            if not isinstance(data["streamingInfo"]["raw"][type], dict):
                continue

            urlpart = data["streamingInfo"]["raw"][type]["location"]
            url = "https://streaming10.ur.se/{}playlist.m3u8".format(urlpart)

            for s in HLSStream.parse_variant_playlist(self.session, url).items():
                yield s


__plugin__ = URPlay
