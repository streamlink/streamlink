import re

from streamlink.compat import bytes, is_py3, unquote_plus, urlencode
from streamlink.plugin import Plugin
from streamlink.plugin.api import useragents
from streamlink.stream import DASHStream, HTTPStream
from streamlink.utils import parse_json


class Facebook(Plugin):
    _url_re = re.compile(r"https?://(?:www\.)?facebook\.com/[^/]+/(posts|videos)")
    _src_re = re.compile(r'''(sd|hd)_src["']?\s*:\s*(?P<quote>["'])(?P<url>.+?)(?P=quote)''')
    _dash_manifest_re = re.compile(r'''dash_manifest["']?\s*:\s*["'](?P<manifest>.+?)["'],''')
    _playlist_re = re.compile(r'''video:\[({url:".+?}\])''')
    _plurl_re = re.compile(r'''url:"(.*?)"''')

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url)

    def _parse_streams(self, res):
        for match in self._src_re.finditer(res.text):
            stream_url = match.group("url")
            if "\\/" in stream_url:
                # if the URL is json encoded, decode it
                stream_url = parse_json("\"{}\"".format(stream_url))
            if ".mpd" in stream_url:
                for s in DASHStream.parse_manifest(self.session, stream_url).items():
                    yield s
            elif ".mp4" in stream_url:
                yield match.group(1), HTTPStream(self.session, stream_url)
            else:
                self.logger.debug("Non-dash/mp4 stream: {0}".format(stream_url))

        match = self._dash_manifest_re.search(res.text)
        if match:
            manifest = match.group("manifest")
            if "\\/" in manifest:
                manifest = manifest.replace("\\/", "/")
            # facebook replaces "<" characters with the substring "\\x3C"
            if is_py3:
                manifest = bytes(unquote_plus(manifest), "utf-8").decode("unicode_escape")
            else:
                manifest = unquote_plus(manifest).decode("string_escape")
            for s in DASHStream.parse_manifest(self.session, None, manifest=manifest).items():
                yield s

    def _get_streams(self):
        done = False
        res = self.session.http.get(self.url, headers={"User-Agent": useragents.CHROME})
        for s in self._parse_streams(res):
            done = True
            yield s
        if done:
            return

        # fallback on to playlist
        self.logger.debug("Falling back to playlist regex")
        match = self._playlist_re.search(res.text)
        playlist = match and match.group(1)
        if playlist:
            match = self._plurl_re.search(playlist)
            if match:
                url = match.group(1)
                yield "sd", HTTPStream(self.session, url)
                return



__plugin__ = Facebook
