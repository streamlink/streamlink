import re

from streamlink import PluginError
from streamlink.plugin import Plugin, PluginArguments, PluginArgument
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream
from streamlink.stream import RTMPStream
from streamlink.plugin.api import http
from streamlink.compat import urljoin


class LiveEdu(Plugin):
    login_url = "https://www.liveedu.tv/accounts/login/"
    url_re = re.compile(r"https?://(?:\w+\.)?(?:livecoding|liveedu)\.tv/")
    config_re = re.compile(r"""\Wconfig.(?P<key>\w+)\s*=\s*(?P<q>['"])(?P<value>.*?)(?P=q);""")
    csrf_re = re.compile(r'''"csrfToken"\s*:\s*"(\w+)"''')
    api_schema = validate.Schema({
        "viewing_urls": {
            validate.optional("error"): validate.text,
            validate.optional("urls"): [{
                "src": validate.url(),
                "type": validate.text,
                validate.optional("res"): int,
                validate.optional("label"): validate.text,
            }]
        }
    })
    config_schema = validate.Schema({
        "selectedVideoHID": validate.text,
        "livestreamURL": validate.text,
        "videosURL": validate.text
    })

    arguments = PluginArguments(
        PluginArgument(
            "email",
            requires=["password"],
            metavar="EMAIL",
            help="The email address used to register with liveedu.tv."
        ),
        PluginArgument(
            "password",
            sensitive=True,
            metavar="PASSWORD",
            help="A LiveEdu account password to use with --liveedu-email."
        )
    )

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def login(self):
        """
        Attempt a login to LiveEdu.tv
        """
        email = self.get_option("email")
        password = self.get_option("password")

        if email and password:
            res = http.get(self.login_url)
            csrf_match = self.csrf_re.search(res.text)
            token = csrf_match and csrf_match.group(1)
            self.logger.debug("Attempting login as {0} (token={1})", email, token)

            res = http.post(self.login_url,
                            data=dict(login=email, password=password, csrfmiddlewaretoken=token),
                            allow_redirects=False,
                            raise_for_status=False,
                            headers={"Referer": self.login_url})

            if res.status_code != 302:
                self.logger.error("Failed to login to LiveEdu account: {0}", email)

    def _get_streams(self):
        """
        Get the config object from the page source and call the
        API to get the list of streams
        :return:
        """
        # attempt a login
        self.login()

        res = http.get(self.url)
        # decode the config for the page
        matches = self.config_re.finditer(res.text)
        try:
            config = self.config_schema.validate(dict(
                [m.group("key", "value") for m in matches]
            ))
        except PluginError:
            return

        if config["selectedVideoHID"]:
            self.logger.debug("Found video hash ID: {0}", config["selectedVideoHID"])
            api_url = urljoin(self.url, urljoin(config["videosURL"], config["selectedVideoHID"]))
        elif config["livestreamURL"]:
            self.logger.debug("Found live stream URL: {0}", config["livestreamURL"])
            api_url = urljoin(self.url, config["livestreamURL"])
        else:
            return

        ares = http.get(api_url)
        data = http.json(ares, schema=self.api_schema)
        viewing_urls = data["viewing_urls"]

        if "error" in viewing_urls:
            self.logger.error("Failed to load streams: {0}", viewing_urls["error"])
        else:
            for url in viewing_urls["urls"]:
                try:
                    label = "{0}p".format(url.get("res", url["label"]))
                except KeyError:
                    label = "live"

                if url["type"] == "rtmp/mp4" and RTMPStream.is_usable(self.session):
                    params = {
                        "rtmp": url["src"],
                        "pageUrl": self.url,
                        "live": True,
                    }
                    yield label, RTMPStream(self.session, params)

                elif url["type"] == "application/x-mpegURL":
                    for s in HLSStream.parse_variant_playlist(self.session, url["src"]).items():
                        yield s


__plugin__ = LiveEdu
