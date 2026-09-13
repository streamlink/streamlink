"""
$description Chinese, global live-streaming platform run by Huya Live.
$url nimo.tv
$type live
$metadata author
$metadata category
$metadata title
"""

import re
from base64 import b64decode
from hashlib import md5
from time import time
from urllib.parse import unquote

from streamlink.logger import getLogger
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import useragents, validate
from streamlink.stream.hls import HLSStream
from streamlink.utils.url import update_scheme


log = getLogger(__name__)


@pluginmatcher(
    re.compile(r"https?://(?:www\.|m\.)?nimo\.tv/(?P<channel>(?:live/\d+)?[^/?#]+)"),
)
class NimoTV(Plugin):
    data_url = "https://m.nimo.tv/{0}"

    video_qualities = {
        250: "240p",
        500: "360p",
        1000: "480p",
        2000: "720p",
        6000: "1080p",
    }

    _re_appid = re.compile(rb"appid=(\d+)")
    _re_domain = re.compile(rb"(https?:\/\/[A-Za-z]{2,3}.hls[A-Za-z\.\/]+)(?:V|&)")
    _re_id = re.compile(rb"id=([^|\\]+)")
    _re_tp = re.compile(rb"tp=(\d+)")
    _re_fm = re.compile(rb"fm=([^&]+)")
    _re_ctype = re.compile(rb"ctype=([^A-Z]+)")
    _re_wsTime = re.compile(rb"wsTime=(\w+)")

    def _get_secret(self, fm: str, stream_name: str, ws_time: str) -> dict:
        uid = 0
        now = int(time() * 1000)
        seqid = uid + now
        prefix = b64decode(unquote(fm).encode()).decode().split("_")[0]
        secret = md5(f"{prefix}_{uid}_{stream_name}_{seqid}_{ws_time}".encode()).hexdigest()
        return {
            "wsSecret": secret,
            "seqid": seqid,
            "u": uid,
        }

    def _get_streams(self):
        self.session.http.headers.update({
            "User-Agent": useragents.ANDROID,
            "Referer": "https://m.nimo.tv/",
        })

        data = self.session.http.get(
            self.data_url.format(self.match["channel"]),
            schema=validate.Schema(
                re.compile(r"<script>var G_roomBaseInfo = ({.*?});</script>"),
                validate.none_or_all(
                    validate.get(1),
                    validate.parse_json(),
                    {
                        "nickname": str,
                        "game": str,
                        "title": str,
                        "liveStreamStatus": int,
                        validate.optional("mStreamPkg"): str,
                    },
                    validate.union_get(
                        "nickname",
                        "game",
                        "title",
                        "liveStreamStatus",
                        "mStreamPkg",
                    ),
                ),
            ),
        )

        if not data:
            return

        self.author, self.category, self.title, online, mStreamPkg = data

        if online == 0:
            log.info("This stream is currently offline")
            return

        if not mStreamPkg:
            log.error("missing mStreamPkg")
            return

        mStreamPkg = bytes.fromhex(mStreamPkg)
        try:  # ruff: ignore[too-many-statements-in-try-clause]
            appid = self._re_appid.search(mStreamPkg).group(1).decode("utf-8")  # type: ignore[ty:unresolved-attribute]
            domain = self._re_domain.search(mStreamPkg).group(1).decode("utf-8")  # type: ignore[ty:unresolved-attribute]
            id_ = self._re_id.search(mStreamPkg).group(1).decode("utf-8")  # type: ignore[ty:unresolved-attribute]
            tp = self._re_tp.search(mStreamPkg).group(1).decode("utf-8")  # type: ignore[ty:unresolved-attribute]
            fm = self._re_fm.search(mStreamPkg).group(1).decode("utf-8")  # type: ignore[ty:unresolved-attribute]
            ctype = self._re_ctype.search(mStreamPkg).group(1).decode("utf-8")  # type: ignore[ty:unresolved-attribute]
            ws_time = self._re_wsTime.search(mStreamPkg).group(1).decode("utf-8")  # type: ignore[ty:unresolved-attribute]
        except AttributeError:
            log.error("invalid mStreamPkg")
            return

        secret = self._get_secret(fm, id_, ws_time)

        params = {
            "appid": appid,
            "ctype": ctype,
            "id": id_,
            "tp": tp,
            "wsTime": ws_time,
            "t": "110",
            "sv": 2411271811,
            **secret,
        }

        url = update_scheme("https://", f"{domain}{id_}.m3u8")
        log.debug(f"URL={url}")
        for k, v in self.video_qualities.items():
            params = params.copy()
            params["ratio"] = k
            log.trace("%s params=%r", v, params)
            # some qualities might not exist, but it will select a different lower quality
            yield v, HLSStream(self.session, url, params=params)


__plugin__ = NimoTV
