"""
$description Chinese, global live-streaming platform run by Huya Live.
$url nimo.tv
$type live
$metadata author
$metadata category
$metadata title
"""

import logging
import re

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import useragents, validate
from streamlink.stream.http import HTTPStream


log = logging.getLogger(__name__)


@pluginmatcher(
    re.compile(r"https?://(?:www\.|m\.)?nimo\.tv/(?P<username>.*)"),
)
class NimoTV(Plugin):
    data_url = "https://m.nimo.tv/{0}"

    video_qualities = {
        250: "240p",
        500: "360p",
        1000: "480p",
        2500: "720p",
        6000: "1080p",
    }

    _re_appid = re.compile(rb"appid=(\d+)")
    _re_domain = re.compile(rb"(https?:\/\/[A-Za-z]{2,3}.hls[A-Za-z\.\/]+)(?:V|&)")
    _re_id = re.compile(rb"id=([^|\\]+)")
    _re_tp = re.compile(rb"tp=(\d+)")
    _re_wsSecret = re.compile(rb"wsSecret=(\w+)")
    _re_wsTime = re.compile(rb"wsTime=(\w+)")

    def _get_streams(self):
        username = self.match.group("username")
        if not username:
            return

        data = self.session.http.get(
            self.data_url.format(username),
            headers={
                "User-Agent": useragents.ANDROID,
            },
            schema=validate.Schema(
                re.compile(r"<script>var G_roomBaseInfo = ({.*?});</script>"),
                validate.none_or_all(
                    validate.get(1),
                    validate.parse_json(),
                    {
                        "title": str,
                        "nickname": str,
                        "game": str,
                        "liveStreamStatus": int,
                        validate.optional("mStreamPkg"): str,
                    },
                ),
            ),
        )

        if data["liveStreamStatus"] == 0:
            log.info("This stream is currently offline")
            return

        mStreamPkg = data.get("mStreamPkg")
        if not mStreamPkg:
            log.debug("missing mStreamPkg")
            return

        mStreamPkg = bytes.fromhex(mStreamPkg)
        try:
            _appid = self._re_appid.search(mStreamPkg).group(1).decode("utf-8")
            _domain = self._re_domain.search(mStreamPkg).group(1).decode("utf-8")
            _id = self._re_id.search(mStreamPkg).group(1).decode("utf-8")
            _tp = self._re_tp.search(mStreamPkg).group(1).decode("utf-8")
            _wsSecret = self._re_wsSecret.search(mStreamPkg).group(1).decode("utf-8")
            _wsTime = self._re_wsTime.search(mStreamPkg).group(1).decode("utf-8")
        except AttributeError:
            log.error("invalid mStreamPkg")
            return

        params = {
            "appid": _appid,
            "id": _id,
            "tp": _tp,
            "wsSecret": _wsSecret,
            "wsTime": _wsTime,
            "u": "0",
            "t": "100",
            "needwm": 1,
        }
        url = f"{_domain}{_id}.flv"
        url = url.replace("hls.nimo.tv", "flv.nimo.tv")
        log.debug(f"URL={url}")
        for k, v in self.video_qualities.items():
            _params = params.copy()
            _params["ratio"] = k
            if v == "1080p":
                _params["needwm"] = 0
            elif v in ("720p", "480p", "360p"):
                _params["sphd"] = 1

            log.trace(f"{v} params={_params!r}")
            # some qualities might not exist, but it will select a different lower quality
            yield v, HTTPStream(self.session, url, params=_params)

        self.author = data["nickname"]
        self.category = data["game"]
        self.title = data["title"]


__plugin__ = NimoTV
