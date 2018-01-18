import re

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


def js_to_json_regex_fallback(js_data):
    """Regex fallback if js_to_json fails"""
    data_re = re.compile(r"""(?<!\w)(?P<name>id|name|type)["']?:\s?["']?(?P<data>[^"']+)["']?(?:,|(?:\s+)?})""")
    data_all = data_re.findall(js_data)
    data_new = {}
    for name, data in data_all:
        data_new[name] = data
    return data_new


class Neulion(Plugin):
    """Streamlink Plugin for websites based on Neulion
       Example urls can be found in tests/test_plugin_neulion.py
    """

    url_re = re.compile(r"""https?://
        (?P<domain>
            www\.(?:
                ufc\.tv
                |
                elevensports\.(?:be|lu|pl|sg|tw)
                |
                tennischanneleverywhere\.com
                )
            |
            watch\.(?:
                nba\.com
                |
                rugbypass\.com
                )
            |
            fanpass\.co\.nz
        )
        /(?P<vtype>channel|game|video)/.+""", re.VERBOSE)
    video_info_re = re.compile(r"""program\s*=\s*(\{.*?});""", re.DOTALL)
    channel_info_re = re.compile(r"""g_channel\s*=\s(\{.*?});""", re.DOTALL)
    current_video_re = re.compile(r"""(?:currentVideo|video)\s*=\s*(\{[^;]+});""", re.DOTALL)
    info_fallback_re = re.compile(r"""
        var\s?
        (?:
            currentGameId
        |
            programId
        )
        \s?=\s?["']?(?P<id>\d+)["']?;
        """, re.VERBOSE)

    stream_api_url = "https://{0}/service/publishpoint"
    auth_url = "https://{0}/secure/authenticate"
    auth_schema = validate.Schema(validate.xml_findtext("code"))

    options = PluginOptions({
        "username": None,
        "password": None
    })

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    @property
    def _domain(self):
        match = self.url_re.match(self.url)
        return match.group("domain")

    @property
    def _vtype(self):
        match = self.url_re.match(self.url)
        return match.group("vtype")

    def _get_stream_url(self, video_id, vtype):
        try:
            res = http.post(self.stream_api_url.format(self._domain), data={
                "id": video_id,
                "type": vtype,
                "format": "json"
            }, headers={
                "User-Agent": useragents.IPHONE_6
            })
        except Exception as e:
            if "400 Client Error" in str(e):
                self.logger.error("Login required")
                return
            else:
                raise e

        data = http.json(res)
        return data.get("path")

    def _get_info(self, text):
        # try to find video info first
        m = self.video_info_re.search(text)
        if not m:
            m = self.current_video_re.search(text)
        if not m:
            # and channel info if that fails
            m = self.channel_info_re.search(text)
        if m:
            js_data = m.group(1)
            try:
                return_data = js_to_json(js_data)
                self.logger.debug("js_to_json")
            except Exception as e:
                self.logger.debug("js_to_json_regex_fallback")
                return_data = js_to_json_regex_fallback(js_data)
            finally:
                return return_data

    def _get_info_fallback(self, text):
        info_id = self.info_fallback_re.search(text)
        if info_id:
            self.logger.debug("Found id from _get_info_fallback")
            return {"id": info_id.group("id")}

    def _login(self, username, password):
        res = http.post(self.auth_url.format(self._domain), data={
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
        login_username = self.get_option("username")
        login_password = self.get_option("password")
        if login_username and login_password:
            self.logger.debug("Attempting login as {0}", login_username)
            if self._login(login_username, login_password):
                self.logger.info("Successfully logged in as {0}", login_username)
            else:
                self.logger.info("Failed to login as {0}", login_username)

        res = http.get(self.url)
        video = self._get_info(res.text)
        if not video:
            video = self._get_info_fallback(res.text)

        if video:
            self.logger.debug("Found {type}: {name}".format(
                type=video.get("type", self._vtype),
                name=video.get("name", "???")
            ))
            surl = self._get_stream_url(video["id"], video.get("type", self._vtype))
            if surl:
                surl = surl.replace("_iphone", "")
                return HLSStream.parse_variant_playlist(self.session, surl)
            else:
                self.logger.error("Could not get stream URL for video: {name} ({id})".format(
                    id=video.get("id", "???"),
                    name=video.get("name", "???"),
                ))
        else:
            self.logger.error("Could not find any video info on the page")


__plugin__ = Neulion
