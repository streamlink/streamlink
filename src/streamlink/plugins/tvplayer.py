import logging
import re

from streamlink.plugin import Plugin, PluginArgument, PluginArguments
from streamlink.plugin.api import useragents, validate
from streamlink.stream import HLSStream

log = logging.getLogger(__name__)


class TVPlayer(Plugin):
    api_url = "https://v1-streams-elb.tvplayer-cdn.com/api/live/stream/"
    stream_url = "https://live.tvplayer.com/stream-live.php"
    login_url = "https://v1-auth.tvplayer-cdn.com/login?responseType=redirect&redirectUri=https://tvplayer.com/login&lang=en"
    update_url = "https://tvplayer.com/account/update-detail"
    dummy_postcode = "SE1 9LT"  # location of ITV HQ in London

    url_re = re.compile(r"https?://(?:www\.)?tvplayer\.com/(:?uk/)?(:?watch/?|watch/(.+)?)")
    stream_attrs_re = re.compile(r'data-player-(expiry|key|token|uvid)\s*=\s*"(.*?)"', re.S)
    login_token_re = re.compile(r'input.*?name="_token".*?value="(\w+)"')
    stream_schema = validate.Schema({
        "response": validate.Schema({
            "stream": validate.any(None, validate.text),
            "drm": validate.any(None, validate.text)
        })
    })
    arguments = PluginArguments(
        PluginArgument(
            "email",
            help="The email address used to register with tvplayer.com.",
            metavar="EMAIL",
            requires=["password"]
        ),
        PluginArgument(
            "password",
            sensitive=True,
            help="The password for your tvplayer.com account.",
            metavar="PASSWORD"
        )
    )

    @classmethod
    def can_handle_url(cls, url):
        match = TVPlayer.url_re.match(url)
        return match is not None

    def __init__(self, url):
        super().__init__(url)
        self.session.http.headers.update({"User-Agent": useragents.CHROME})

    def authenticate(self, username, password):
        res = self.session.http.get(self.login_url)
        match = self.login_token_re.search(res.text)
        token = match and match.group(1)
        res2 = self.session.http.post(
            self.login_url,
            data=dict(email=username, password=password, _token=token),
            allow_redirects=False
        )
        # there is a 302 redirect on a successful login
        return res2.status_code == 302

    def _get_stream_data(self, expiry, key, token, uvid):
        res = self.session.http.get(
            self.api_url + uvid,
            params=dict(key=key, platform="chrome"),
            headers={
                "Token": token,
                "Token-Expiry": expiry,
                "Uvid": uvid
            }
        )

        res_schema = self.session.http.json(res, schema=self.stream_schema)

        if res_schema["response"]["stream"] is None:
            res = self.session.http.get(
                self.stream_url,
                params=dict(key=key, platform="chrome"),
                headers={
                    "Token": token,
                    "Token-Expiry": expiry,
                    "Uvid": uvid
                }
            ).json()
            res_schema["response"]["stream"] = res["Streams"]["Adaptive"]

        return res_schema

    def _get_stream_attrs(self, page):
        stream_attrs = {k.replace("-", "_"): v.strip('"') for k, v in self.stream_attrs_re.findall(page.text)}

        log.debug(f"Got stream attributes: {str(stream_attrs)}")
        valid = True
        for a in ("expiry", "key", "token", "uvid"):
            if a not in stream_attrs:
                log.debug(f"Missing '{a}' from stream attributes")
                valid = False

        return stream_attrs if valid else {}

    def _get_streams(self):
        if self.get_option("email") and self.get_option("password"):
            log.debug("Logging in as {0}".format(self.get_option("email")))
            if not self.authenticate(self.get_option("email"), self.get_option("password")):
                log.warning("Failed to login as {0}".format(self.get_option("email")))

        # find the list of channels from the html in the page
        self.url = self.url.replace("https", "http")  # https redirects to http
        res = self.session.http.get(self.url)

        if "enter your postcode" in res.text:
            log.info(
                f"Setting your postcode to: {self.dummy_postcode}. "
                f"This can be changed in the settings on tvplayer.com"
            )
            res = self.session.http.post(
                self.update_url,
                data=dict(postcode=self.dummy_postcode),
                params=dict(return_url=self.url)
            )

        stream_attrs = self._get_stream_attrs(res)
        if stream_attrs:
            stream_data = self._get_stream_data(**stream_attrs)

            if stream_data:
                if stream_data["response"]["drm"] is not None:
                    log.error("This stream is protected by DRM can cannot be played")
                    return
                else:
                    return HLSStream.parse_variant_playlist(
                        self.session, stream_data["response"]["stream"]
                    )
        else:
            if "need to login" in res.text:
                log.error(
                    "You need to login using --tvplayer-email/--tvplayer-password to view this stream")


__plugin__ = TVPlayer
