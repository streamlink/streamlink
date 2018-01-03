from __future__ import print_function

import re
import string
from functools import partial

from streamlink.plugin import Plugin, PluginOptions
from streamlink.plugin.api import http
from streamlink.plugin.api import useragents
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream
from streamlink.utils import parse_json


def js_to_json(data):
    js_re = re.compile(r'(?!<")(\w+):(?!/)')
    trimmed = [y.replace("\r", "").strip() for y in data.split(",")]
    jsons = ','.join([js_re.sub(r'"\1":', x, count=1) for x in trimmed])
    return parse_json(jsons)


class UFCTV(Plugin):
    url_re = re.compile(r"https?://(?:www\.)?ufc\.tv/(channel|video)/.+")
    video_info_re = re.compile(r"""program\s*=\s*(\{.*?});""", re.DOTALL)
    channel_info_re = re.compile(r"""g_channel\s*=\s(\{.*?});""", re.DOTALL)

    stream_api_url = "https://www.ufc.tv/service/publishpoint"
    auth_url = "https://www.ufc.tv/secure/authenticate"
    auth_schema = validate.Schema(validate.xml_findtext("code"))

    options = PluginOptions({
        "username": None,
        "password": None
    })

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def _get_stream_url(self, video_id, vtype="video"):
        res = http.post(self.stream_api_url, data={
            "id": video_id,
            "type": vtype,
            "format": "json"
        }, headers={
            "User-Agent": useragents.IPHONE_6
        })
        data = http.json(res)
        return data.get("path")

    def _get_info(self, url):
        res = http.get(url)
        # try to find video info first
        m = self.video_info_re.search(res.text)
        if not m:
            # and channel info if that fails
            m = self.channel_info_re.search(res.text)
        return m and js_to_json(m.group(1))

    def _login(self, username, password):
        res = http.post(self.auth_url, data={
            "username": username,
            "password": password,
            "cookielink": False
        })
        login_status = http.xml(res, schema=self.auth_schema)
        self.logger.debug("Login status for {0}: {1}", username, login_status)
        if login_status == "loginlocked":
            self.logger.error("The account {0} has been locked, the password needs to be reset")
        return login_status == "loginsuccess"

    def _get_streams(self):
        if self.get_option("username") and self.get_option("password"):
            self.logger.debug("Attempting login as {0}", self.get_option("username"))
            if self._login(self.get_option("username"), self.get_option("password")):
                self.logger.info("Successfully logged in as {0}", self.get_option("username"))
            else:
                self.logger.info("Failed to login as {0}", self.get_option("username"))

        video = self._get_info(self.url)
        if video:
            self.logger.debug("Found {type}: {name}", **video)
            surl = self._get_stream_url(video['id'], video.get('type', "video"))
            surl = surl.replace("_iphone", "")
            if surl:
                return HLSStream.parse_variant_playlist(self.session, surl)
            else:
                self.logger.error("Could not get stream URL for video: {name} ({id})", **video)
        else:
            self.logger.error("Could not find any video info on the page")

__plugin__ = UFCTV
