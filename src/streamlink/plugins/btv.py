from __future__ import print_function
import re

from streamlink import PluginError
from streamlink.plugin import Plugin
from streamlink.plugin.api import http
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream
from streamlink.utils import parse_json
from streamlink.plugin import PluginArgument, PluginArguments


class BTV(Plugin):
    arguments = PluginArguments(
        PluginArgument(
            "username",
            metavar="USERNAME",
            requires=["password"],
            help="""
        A BTV username required to access any stream.
        """
        ),
        PluginArgument(
            "password",
            sensitive=True,
            metavar="PASSWORD",
            help="""
        A BTV account password to use with --btv-username.
        """
        )
    )
    url_re = re.compile(r"https?://(?:www\.)?btv\.bg/live/?")

    api_url = "http://www.btv.bg/lbin/global/player_config.php"
    check_login_url = "http://www.btv.bg/lbin/userRegistration/check_user_login.php"
    login_url = "https://www.btv.bg/bin/registration2/login.php?action=login&settings=0"

    media_id_re = re.compile(r"media_id=(\d+)")
    src_re = re.compile(r"src: \"(http.*?)\"")
    api_schema = validate.Schema(
        validate.all(
            {"status": "ok", "config": validate.text},
            validate.get("config"),
            validate.all(validate.transform(src_re.search),
                         validate.any(
                             None,
                             validate.get(1), validate.url()
                         ))
        )
    )

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def login(self, username, password):
        res = http.post(self.login_url, data={"username": username, "password": password})
        if "success_logged_in" in res.text:
            return True
        else:
            return False

    def get_hls_url(self, media_id):
        res = http.get(self.api_url, params=dict(media_id=media_id))
        try:
            return parse_json(res.text, schema=self.api_schema)
        except PluginError:
            return

    def _get_streams(self):
        if not self.options.get("username") or not self.options.get("password"):
            self.logger.error("BTV requires registration, set the username and password"
                              " with --btv-username and --btv-password")
        elif self.login(self.options.get("username"), self.options.get("password")):
            res = http.get(self.url)
            media_match = self.media_id_re.search(res.text)
            media_id = media_match and media_match.group(1)
            if media_id:
                self.logger.debug("Found media id: {0}", media_id)
                stream_url = self.get_hls_url(media_id)
                if stream_url:
                    return HLSStream.parse_variant_playlist(self.session, stream_url)
        else:
            self.logger.error("Login failed, a valid username and password is required")


__plugin__ = BTV
