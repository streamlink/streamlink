import re

from streamlink.plugin import Plugin, PluginError, PluginOptions
from streamlink.plugin.api import http, validate
from streamlink.stream import HLSStream

LOGIN_PAGE_URL = "http://www.livestation.com/en/users/new"
LOGIN_POST_URL = "http://www.livestation.com/en/sessions.json"

_csrf_token_re = re.compile("<meta content=\"([^\"]+)\" name=\"csrf-token\"")
_hls_playlist_re = re.compile("<meta content=\"([^\"]+.m3u8)\" property=\"og:video\" />")
_url_re = re.compile("http(s)?://(\w+\.)?livestation.com")

_csrf_token_schema = validate.Schema(
    validate.transform(_csrf_token_re.search),
    validate.any(None, validate.get(1))
)
_hls_playlist_schema = validate.Schema(
    validate.transform(_hls_playlist_re.search),
    validate.any(
        None,
        validate.all(
            validate.get(1),
            validate.url(scheme="http", path=validate.endswith(".m3u8"))
        )
    )
)
_login_schema = validate.Schema({
    "email": validate.text,
    validate.optional("errors"): validate.all(
        {
            "base": [validate.text]
        },
        validate.get("base"),
    )
})


class Livestation(Plugin):
    options = PluginOptions({
        "email": "",
        "password": ""
    })

    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    def _authenticate(self, email, password):
        csrf_token = http.get(LOGIN_PAGE_URL, schema=_csrf_token_schema)
        if not csrf_token:
            raise PluginError("Unable to find CSRF token")

        data = {
            "authenticity_token": csrf_token,
            "channel_id": "",
            "commit": "Login",
            "plan_id": "",
            "session[email]": email,
            "session[password]": password,
            "utf8": "\xE2\x9C\x93", # Check Mark Character
        }

        res = http.post(LOGIN_POST_URL, data=data, acceptable_status=(200, 422))
        result = http.json(res, schema=_login_schema)

        errors = result.get("errors")
        if errors:
            errors = ", ".join(errors)
            raise PluginError("Unable to authenticate: {0}".format(errors))

        self.logger.info("Successfully logged in as {0}", result["email"])

    def _get_streams(self):
        login_email = self.options.get("email")
        login_password = self.options.get("password")
        if login_email and login_password:
            self._authenticate(login_email, login_password)

        hls_playlist = http.get(self.url, schema=_hls_playlist_schema)
        if not hls_playlist:
            return

        return HLSStream.parse_variant_playlist(self.session, hls_playlist)


__plugin__ = Livestation

