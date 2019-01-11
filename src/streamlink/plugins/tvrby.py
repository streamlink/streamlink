import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream


class TVRBy(Plugin):
    url_re = re.compile(r"""https?://(?:www\.)?tvr.by/televidenie/belarus""")
    file_re = re.compile(r"""(?P<url>https://stream\.hoster\.by[^"',]+\.m3u8[^"',]*)""")
    player_re = re.compile(r"""["'](?P<url>[^"']+tvr\.by/plugines/online-tv-main\.php[^"']+)["']""")

    stream_schema = validate.Schema(
        validate.all(
            validate.transform(file_re.finditer),
            validate.transform(list),
            [validate.get("url")],
            # remove duplicates
            validate.transform(set),
            validate.transform(list),
        ),
    )

    def __init__(self, url):
        # ensure the URL ends with a /
        if not url.endswith("/"):
            url += "/"
        super(TVRBy, self).__init__(url)

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_streams(self):
        res = self.session.http.get(self.url)
        m = self.player_re.search(res.text)
        if not m:
            return

        player_url = m.group("url")
        res = self.session.http.get(player_url)
        stream_urls = self.stream_schema.validate(res.text)
        self.logger.debug("Found {0} stream URL{1}", len(stream_urls),
                          "" if len(stream_urls) == 1 else "s")

        for stream_url in stream_urls:
            for s in HLSStream.parse_variant_playlist(self.session, stream_url).items():
                yield s


__plugin__ = TVRBy
