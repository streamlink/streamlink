"""Plugin for RUV, the Icelandic national television."""

import re

from streamlink.plugin import Plugin
from streamlink.stream import HLSStream

from streamlink.plugin.api import http

HLS_RUV_LIVE_URL = """http://ruvruv-live.hls.adaptive.level3.net/ruv/{0}/\
index/stream{1}.m3u8"""

HLS_RADIO_LIVE_URL = """http://sip-live.hds.adaptive.level3.net/hls-live/\
ruv-{0}/_definst_/live/stream1.m3u8"""

HLS_SARPURINN_URL = """http://sip-ruv-vod.dcp.adaptive.level3.net/\
{0}/{1}{2}"""


_live_url_re = re.compile(r"""^(?:https?://)?(?:www\.)?ruv\.is/
                                (?P<stream_id>
                                    ruv/?$|
                                    ruv2/?$|
                                    ruv-2/?$|
                                    ras1/?$|
                                    ras2/?$|
                                    rondo/?$
                                )
                                /?
                                """, re.VERBOSE)

_sarpurinn_url_re = re.compile(r"""^(?:https?://)?(?:www\.)?ruv\.is/spila/
                                    (?P<stream_id>
                                        ruv|
                                        ruv2|
                                        ruv-2|
                                        ruv-aukaras|
                                    )
                                    /
                                    [a-zA-Z0-9_-]+
                                    /
                                    [0-9]+
                                    /?
                                    """, re.VERBOSE)

_single_re = re.compile(r"""(?:http://)?sip-ruv-vod.dcp.adaptive.level3.net/
                            (?P<status>
                                lokad|
                                opid
                            )
                            /
                            (?P<date>[0-9]+/[0-9][0-9]/[0-9][0-9]/)?
                            (?P<id>[A-Z0-9\$_]+)
                            \.mp4\.m3u8
                         """, re.VERBOSE)

_multi_re = re.compile(r"""(?:http://)?sip-ruv-vod.dcp.adaptive.level3.net/
                            (?P<status>
                                lokad|
                                opid
                            )
                            /manifest.m3u8\?tlm=hls&streams=
                            (?P<streams>[0-9a-zA-Z\/\.\,:]+)
                         """, re.VERBOSE)

class Ruv(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        if _live_url_re.match(url):
            return True
        else:
            return _sarpurinn_url_re.match(url)

    def __init__(self, url):
        Plugin.__init__(self, url)
        live_match = _live_url_re.match(url)

        if live_match:
            self.live = True
            self.stream_id = live_match.group("stream_id")

            # Remove slashes
            self.stream_id.replace("/", "")

            # Remove dashes
            self.stream_id.replace("-", "")

            if self.stream_id == "rondo":
                self.stream_id = "ras3"
        else:
            self.live = False

    def _get_live_streams(self):
        if self.stream_id == "ruv" or self.stream_id == "ruv2":
            qualities_hls = ["240p", "360p", "480p", "720p"]
            for i, quality_hls in enumerate(qualities_hls):
                yield quality_hls, HLSStream(
                    self.session,
                    HLS_RUV_LIVE_URL.format(self.stream_id, i+1)
                )
        else:
            yield "audio", HLSStream(
                self.session,
                HLS_RADIO_LIVE_URL.format(self.stream_id)
            )

    def _get_sarpurinn_streams(self):
        res = http.get(self.url)

        multi_stream_match = _multi_re.search(res.text)

        if multi_stream_match and multi_stream_match.group("streams") is not None:
            status = multi_stream_match.group("status")
            streams = multi_stream_match.group("streams").split(",")

            for stream in streams:
                if stream.count(":") != 1:
                    continue

                [url, quality] = stream.split(":")
                quality = int(quality)
                key = ""

                if quality <= 500:
                  key = "240p"
                elif quality <= 800:
                  key = "360p"
                elif quality <= 1200:
                  key = "480p"
                elif quality <= 2400:
                  key = "720p"
                else:
                  key = "1080p"

                yield key, HLSStream(
                    self.session,
                    HLS_SARPURINN_URL.format(status, "", url)
                )

        else:
            single_stream_match = _single_re.search(res.text)

            if single_stream_match:
                status = single_stream_match.group("status")
                date = single_stream_match.group("date")
                token = single_stream_match.group("id")
                key = "576p"

                # Set date as an empty string instread of None
                if date is None:
                    date = ""

                yield key, HLSStream(
                    self.session,
                    HLS_SARPURINN_URL.format(status, date, token + ".mp4.m3u8")
                )

    def _get_streams(self):
        if self.live:
            return self._get_live_streams()
        else:
            return self._get_sarpurinn_streams()


__plugin__ = Ruv
