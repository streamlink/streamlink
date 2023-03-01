"""
$description Ukrainian live TV channels from 1 + 1 Media group, including 1 + 1, 2 + 2, PLUSPLUS, TET and UNIAN.
$url 1plus1.video
$type live
"""

import logging
import re
from base64 import b64decode
from time import time
from urllib.parse import urljoin, urlparse

from streamlink.exceptions import NoStreamsError, PluginError
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream
from streamlink.utils.times import fromlocaltimestamp


log = logging.getLogger(__name__)


class OnePlusOneHLS(HLSStream):
    __shortname__ = "hls-oneplusone"

    def __init__(self, session_, url, self_url=None, **args):
        super().__init__(session_, url, None, **args)
        self._url = url

        first_parsed = urlparse(self._url)
        self._first_netloc = first_parsed.netloc
        self._first_path_chunklist = first_parsed.path.split("/")[-1]
        self.watch_timeout = int(first_parsed.path.split("/")[2]) - 15
        self.api = OnePlusOneAPI(session_, self_url)

    def _next_watch_timeout(self):
        _next = fromlocaltimestamp(self.watch_timeout).isoformat(" ")
        log.debug(f"next watch_timeout at {_next}")

    def open(self):
        self._next_watch_timeout()
        return super().open()

    @property
    def url(self):
        if int(time()) >= self.watch_timeout:
            log.debug("Reloading HLS URL")
            _hls_url = self.api.get_hls_url()
            if not _hls_url:
                self.watch_timeout += 10
                return self._url
            parsed = urlparse(_hls_url)
            path_parts = parsed.path.split("/")
            path_parts[-1] = self._first_path_chunklist
            self.watch_timeout = int(path_parts[2]) - 15
            self._next_watch_timeout()

            self._url = parsed._replace(
                netloc=self._first_netloc,
                path="/".join(list(path_parts)),
            ).geturl()
        return self._url


class OnePlusOneAPI:
    def __init__(self, session, url):
        self.session = session
        self.url = url

    def get_hls_url(self):
        self.session.http.cookies.clear()
        url_parts = self.session.http.get(
            url=self.url,
            schema=validate.Schema(
                validate.parse_html(),
                validate.xml_xpath_string(".//iframe[contains(@src,'embed')]/@src"),
            ),
        )
        if not url_parts:
            raise NoStreamsError

        log.trace(f"url_parts={url_parts}")
        self.session.http.headers.update({"Referer": self.url})

        try:
            url_ovva = self.session.http.get(
                url=urljoin(self.url, url_parts),
                schema=validate.Schema(
                    validate.parse_html(),
                    validate.xml_xpath_string(".//script[@type='text/javascript'][contains(text(),'ovva-player')]/text()"),
                    str,
                    validate.regex(re.compile(r"ovva-player\",\"([^\"]*)\"\)")),
                    validate.get(1),
                    validate.transform(lambda x: b64decode(x).decode()),
                    validate.parse_json(),
                    {"balancer": validate.url()},
                    validate.get("balancer"),
                ))
        except PluginError as err:
            log.error(f"ovva-player: {err}")
            return

        log.debug(f"url_ovva={url_ovva}")
        return self.session.http.get(
            url=url_ovva,
            schema=validate.Schema(
                validate.transform(lambda x: x.split("=")),
                ["302", validate.url(path=validate.endswith(".m3u8"))],
                validate.get(1),
            ),
        )


@pluginmatcher(re.compile(
    r"https?://1plus1\.video/(?:\w{2}/)?tvguide/[^/]+/online",
))
class OnePlusOne(Plugin):
    def _get_streams(self):
        self.api = OnePlusOneAPI(self.session, self.url)
        url_hls = self.api.get_hls_url()
        if not url_hls:
            return
        for q, s in HLSStream.parse_variant_playlist(self.session, url_hls).items():
            yield q, OnePlusOneHLS(self.session, s.url, self_url=self.url)


__plugin__ = OnePlusOne
