from __future__ import print_function

import logging
import re

from streamlink.exceptions import PluginError
from streamlink.plugin import Plugin, PluginArguments, PluginArgument
from streamlink.plugin.api import useragents
from streamlink.plugin.api import validate
from streamlink.stream import HTTPStream, HLSStream
from streamlink.stream.hls import HLSStreamReader, HLSStreamWriter, HLSStreamWorker
from streamlink.stream.hls_playlist import M3U8Parser, load as load_hls_playlist
from streamlink.stream.ffmpegmux import MuxedStream

log = logging.getLogger(__name__)

class YottaM3U8Parser(M3U8Parser):
    def __init__(self, base_uri=None, **kwargs):
        super(YottaM3U8Parser, self).__init__(base_uri, **kwargs)

    def parse_extinf(self, value):
        duration, _ = super(YottaM3U8Parser, self).parse_extinf(value)
        return duration, None

class YottaHLSStreamWorker(HLSStreamWorker):
    def _reload_playlist(self, text, url):
        playlist = load_hls_playlist(
            text,
            url,
            parser=YottaM3U8Parser,
        )
        return playlist

class YottaHLSStreamWriter(HLSStreamWriter):
    def write(self, sequence, *args, **kwargs):
        return super(YottaHLSStreamWriter, self).write(sequence, *args, **kwargs)

class YottaHLSStreamReader(HLSStreamReader):
    __worker__ = YottaHLSStreamWorker
    __writer__ = YottaHLSStreamWriter

class YottaHLSStream(HLSStream):
    __shortname__ = "yottahls"
    def __init__(self, *args, **kwargs):
        super(YottaHLSStream, self).__init__(*args, **kwargs)

    def open(self):
        reader = YottaHLSStreamReader(self)
        reader.open()

        return reader

    @classmethod
    def _get_variant_playlist(cls, res):
        return load_hls_playlist(res.text, base_uri=res.url, parser=YottaM3U8Parser)

class Yotta(Plugin):
    url_re = re.compile(r"https://www\.yottau\.com\.tw/course/player/(\d+)/(\d+)")
    login_url = "https://www.yottau.com.tw/member/login"
    list_api_url = "https://www.yottau.com.tw/chapter/list"
    playlist_schema = validate.Schema(
        {
            "data": {
                "current": {
                    "id": int,
                    "video": validate.all([{
                        "file": validate.any(validate.url(scheme="http", path=validate.contains(".mp4")), validate.url(scheme="http", path=validate.endswith(".m3u8"))),
                        "label": validate.text
                    }]),
                    "subtitle": validate.any([{
                        "file": validate.any(None, validate.url(scheme="http", path=validate.contains(".vtt"))),
                    }])
                }
            }
        }
    )
    arguments = PluginArguments(
        PluginArgument(
            "email",
            required=True,
            requires=["password"],
            metavar="EMAIL",
            help="""
        The email associated with your Yotta account,
        required to access any Yotta stream.
        """
        ),
        PluginArgument(
            "password",
            sensitive=True,
            metavar="PASSWORD",
            help="A Yotta account password to use with --yotta-email."
        )
    )

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def login(self, email, password):
        """
        Login to the yotta account and return the users account
        :param email: (str) email for account
        :param password: (str) password for account
        :return: (str) users email
        """
        if self.options.get("email") and self.options.get("password"):
            
            res = self.session.http.post(self.login_url, data={"account": email,
                                                               "password": password})
            
            if res.json()['code'] == 0 :
                return email
            else:
                log.error("login response code {0}", res.json()['code'])
                log.error("Failed to login to Yotta, incorrect email/password combination")
        else:
            log.error("An email and password are required to access Yotta streams")

    def _get_streams(self):
        user = self.login(self.options.get("email"), self.options.get("password"))
        if user:
            log.error("Logged in to Yotta as {0}", user)
            # list api: get playlist.m3u8, 1080p.m3u8 and subtitles
            # url: /{course_id}/l{chapter_id}
            course_id = int(self.url_re.match(self.url).group(1))
            chapter_id = int(self.url_re.match(self.url).group(2))
            res = self.session.http.post(self.list_api_url, headers={"User-Agent": useragents.SAFARI_8}, data={"id": course_id, "chapter_id": chapter_id})
            playlist = self.session.http.json(res, schema=self.playlist_schema)
            videos = playlist['data']['current']['video']
            subtitles = playlist['data']['current']['subtitle']

            #Traditional Chinese subtitle only
            stream_metadata = {}
            subtitle = {}
            if subtitles != []:
                subtitle["chi"] = HTTPStream(self.session, subtitles[0]['file'])
                stream_metadata["s:a:0"] = ["language={0}".format("chi")]
            
            #get playlist.m3u8 and the best quality of video
            video_url = ""
            qualities = []
            for video in videos:
                quality = video['label']
                if "playlist" in video['label']:
                    video_url = video['file']
                else:
                    #"1080P" to int(1080)
                    qualities.append(int(quality[:-1]))
            best = max(qualities)
            try:
                masterStreams = YottaHLSStream.parse_variant_playlist(self.session, video_url)
                stream = masterStreams["{0}p".format(best)]
            except IOError as err:
                err = str(err)
                if "404 Client Error" in err or "Failed to parse playlist" in err:
                    return
                else:
                    raise PluginError(err)

            if subtitle:
                yield "{0}p".format(best), MuxedStream(self.session, stream, subtitles=subtitle)
            else:
                yield "{0}p".format(best), stream
            
__plugin__ = Yotta