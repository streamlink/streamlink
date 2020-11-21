import logging
import re

from streamlink.plugin import Plugin, PluginArgument, PluginArguments
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream
from streamlink.utils import parse_json

log = logging.getLogger(__name__)


class OPENRECtv(Plugin):
    _url_re = re.compile(r"https?://(?:www\.)?openrec.tv/(?:live|movie)/(?P<id>[^/]+)")
    _stores_re = re.compile(r"window.stores\s*=\s*({.*?});", re.DOTALL | re.MULTILINE)
    _config_re = re.compile(r"window.sharedConfig\s*=\s*({.*?});", re.DOTALL | re.MULTILINE)

    api_url = "https://apiv5.openrec.tv/api/v5/movies/{id}/detail"
    login_url = "https://www.openrec.tv/viewapp/v4/mobile/user/login"

    _config_schema = validate.Schema({
        "urls": {
            "apiv5Authorized": validate.url()
        }
    })
    _stores_schema = validate.Schema({
        "moviePageStore": {
            "movieStore": {
                "id": validate.text,
                "title": validate.text,
                "media": {
                    "url": validate.any(None, '', validate.url())
                }
            }
        }
    }, validate.get("moviePageStore"), validate.get("movieStore"))

    _detail_schema = validate.Schema({
        validate.optional("error_message"): validate.text,
        "status": int,
        validate.optional("data"): {
            "type": validate.text,
            "items": [{
                "media": {
                    "url": validate.any(None, validate.url()),
                    "url_dvr": validate.any(None, validate.url())
                }
            }]
        }
    })

    _login_schema = validate.Schema({
        validate.optional("error_message"): validate.text,
        "status": int,
        validate.optional("data"): object
    })

    arguments = PluginArguments(
        PluginArgument(
            "email",
            requires=["password"],
            metavar="EMAIL",
            help="""
            The email associated with your openrectv account,
            required to access any openrectv stream.
            """),
        PluginArgument(
            "password",
            sensitive=True,
            metavar="PASSWORD",
            help="""
            An openrectv account password to use with --openrectv-email.
            """)
    )

    def __init__(self, url):
        super().__init__(url)
        self._pdata = None
        self._pres = None
        self._pconfig = None

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def login(self, email, password):
        res = self.session.http.post(self.login_url, data={"mail": email, "password": password})
        data = self.session.http.json(res, self._login_schema)
        if data["status"] == 0:
            log.debug("Logged in as {0}".format(data["data"]["user_name"]))
        else:
            log.error("Failed to login: {0}".format(data["error_message"]))
        return data["status"] == 0

    def _get_page(self):
        if not self._pres:
            self._pres = self.session.http.get(self.url)
        return self._pres

    def _get_movie_data(self):
        pres = self._get_page()
        match = self._stores_re.search(pres.text)
        if match:
            self._pdata = parse_json(match.group(1), schema=self._stores_schema)

        return self._pdata

    def _get_page_config(self):
        pres = self._get_page()
        match = self._config_re.search(pres.text)
        if match:
            self._pconfig = parse_json(match.group(1))

        return self._pconfig

    def _get_details(self, id):
        config = self._get_page_config()
        api_url = config["urls"]["apiv5Authorized"]
        url = "{base}/movies/{id}/detail".format(base=api_url, id=id)
        res = self.session.http.get(url, headers={
            "access-token": self.session.http.cookies.get("access_token"),
            "uuid": self.session.http.cookies.get("uuid")
        })
        data = self.session.http.json(res, schema=self._detail_schema)

        if data["status"] == 0:
            log.debug("Got valid detail response")
            return data["data"]
        else:
            log.error("Failed to get video stream: {0}".format(data["error_message"]))

    def get_title(self):
        mdata = self._get_movie_data()
        if mdata:
            return mdata["title"]

    def _get_streams(self):
        mdata = self._get_movie_data()
        if mdata:
            log.debug("Found video: {0} ({1})".format(mdata["title"], mdata["id"]))
            if mdata["media"]["url"]:
                yield from HLSStream.parse_variant_playlist(self.session, mdata["media"]["url"]).items()
            elif self.get_option("email") and self.get_option("password"):
                if self.login(self.get_option("email"), self.get_option("password")):
                    details = self._get_details(mdata["id"])
                    if details:
                        for item in details["items"]:
                            yield from HLSStream.parse_variant_playlist(self.session, item["media"]["url"]).items()
            else:
                log.error("You must login to access this stream")


__plugin__ = OPENRECtv
