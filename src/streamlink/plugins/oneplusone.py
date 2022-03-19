"""
$description Ukrainian live TV channels from 1 + 1 Media group, including 1 + 1, 2 + 2, PLUSPLUS, TET and UNIAN.
$url 1plus1.video
$type live
"""

import logging
import re
from base64 import b64decode
from datetime import datetime
from time import time

from streamlink.compat import urljoin, urlparse
from streamlink.exceptions import NoStreamsError, PluginError
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)


class OnePlusOneHLS(HLSStream):
    __shortname__ = "hls-oneplusone"

    def __init__(self, session_, url, self_url=None, **args):
        super(OnePlusOneHLS, self).__init__(session_, url, None, **args)
        self._url = url

        first_parsed = urlparse(self._url)
        self._first_netloc = first_parsed.netloc
        self._first_path_chunklist = first_parsed.path.split("/")[-1]
        self.watch_timeout = int(first_parsed.path.split("/")[2]) - 15
        self.api = OnePlusOneAPI(session_, self_url)

    def _next_watch_timeout(self):
        _next = datetime.fromtimestamp(self.watch_timeout).isoformat(" ")
        log.debug("next watch_timeout at {0}".format(_next))

    def open(self):
        self._next_watch_timeout()
        return super(OnePlusOneHLS, self).open()

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
                path="/".join([p for p in path_parts])
            ).geturl()
        return self._url


class OnePlusOneAPI:
    def __init__(self, session, url):
        self.session = session
        self.url = url
        self._re_data = re.compile(r"ovva-player\",\"([^\"]*)\"\)")

    def get_hls_url(self):
        self.session.http.cookies.clear()
        url_parts = self.session.http.get(
            url=self.url,
            schema=validate.Schema(
                validate.parse_html(),
                validate.xml_xpath_string(".//iframe[contains(@src,'embed')]/@src")))
        if not url_parts:
            raise NoStreamsError("Missing url_parts")

        log.trace("url_parts={0}".format(url_parts))
        self.session.http.headers.update({"Referer": self.url})

        try:
            url_ovva = self.session.http.get(
                url=urljoin(self.url, url_parts),
                schema=validate.Schema(
                    validate.parse_html(),
                    validate.xml_xpath_string(".//script[@type='text/javascript'][contains(text(),'ovva-player')]/text()"),
                    validate.text,
                    validate.transform(self._re_data.search),
                    validate.get(1),
                    validate.transform(lambda x: b64decode(x).decode()),
                    validate.parse_json(),
                    {"balancer": validate.url()},
                    validate.get("balancer")
                ))
        except (PluginError, TypeError) as err:
            log.error("ovva-player: {0}".format(err))
            return

        log.debug("url_ovva={0}".format(url_ovva))
        url_hls = self.session.http.get(
            url=url_ovva,
            schema=validate.Schema(
                validate.transform(lambda x: x.split("=")),
                ["302", validate.url(path=validate.endswith(".m3u8"))],
                validate.get(1)))
        return url_hls


@pluginmatcher(re.compile(
    r"https?://1plus1\.video/(?:\w{2}/)?tvguide/[^/]+/online"
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
