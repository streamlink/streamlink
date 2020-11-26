import json
import logging
import re
from urllib.parse import parse_qsl, urlparse

from streamlink import PluginError
from streamlink.plugin import Plugin, PluginArgument, PluginArguments
from streamlink.plugin.api import useragents
from streamlink.stream import HLSStream
from streamlink.utils import memoize
from streamlink.utils.times import seconds_to_hhmmss

log = logging.getLogger(__name__)


class WWENetwork(Plugin):
    url_re = re.compile(r"https?://watch\.wwe\.com/(channel)?")
    site_config_re = re.compile(r'''">window.__data = (\{.*?\})</script>''')
    stream_url = "https://dce-frontoffice.imggaming.com/api/v2/stream/{id}"
    live_url = "https://dce-frontoffice.imggaming.com/api/v2/event/live"
    login_url = "https://dce-frontoffice.imggaming.com/api/v2/login"
    page_config_url = "https://cdn.watch.wwe.com/api/page"
    API_KEY = "cca51ea0-7837-40df-a055-75eb6347b2e7"

    customer_id = 16
    arguments = PluginArguments(
        PluginArgument(
            "email",
            required=True,
            metavar="EMAIL",
            requires=["password"],
            help="""
        The email associated with your WWE Network account,
        required to access any WWE Network stream.
        """
        ),
        PluginArgument(
            "password",
            sensitive=True,
            metavar="PASSWORD",
            help="""
        A WWE Network account password to use with --wwenetwork-email.
        """
        )
    )

    def __init__(self, url):
        super().__init__(url)
        self.session.http.headers.update({"User-Agent": useragents.CHROME})
        self.auth_token = None

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

    def get_title(self):
        return self.item_config['title']

    def request(self, method, url, **kwargs):
        headers = kwargs.pop("headers", {})
        headers.update({"x-api-key": self.API_KEY,
                        "Origin": "https://watch.wwe.com",
                        "Referer": "https://watch.wwe.com/signin",
                        "Accept": "application/json",
                        "Realm": "dce.wwe"})
        if self.auth_token:
            headers["Authorization"] = "Bearer {0}".format(self.auth_token)

        kwargs["raise_for_status"] = False
        log.debug("API request: {0} {1}".format(method, url))
        res = self.session.http.request(method, url, headers=headers, **kwargs)
        data = self.session.http.json(res)

        if "status" in data and data["status"] != 200:
            log.debug("API request failed: {0}:{1} ({2})".format(
                data["status"],
                data.get("code"),
                "; ".join(data.get("messages", []))
            ))
        return data

    def login(self, email, password):
        log.debug("Attempting login as {0}".format(email))
        # sets some required cookies to login
        data = self.request('POST', self.login_url,
                            data=json.dumps({"id": email, "secret": password}),
                            headers={"Content-Type": "application/json"})
        if "authorisationToken" in data:
            self.auth_token = data["authorisationToken"]

        return self.auth_token

    @property
    @memoize
    def item_config(self):
        log.debug("Loading page config")
        p = urlparse(self.url)
        res = self.session.http.get(self.page_config_url,
                                    params=dict(device="web_browser",
                                                ff="idp,ldp",
                                                item_detail_expand="all",
                                                lang="en-US",
                                                list_page_size="1",
                                                max_list_prefetch="1",
                                                path=p.path,
                                                segments="es",
                                                sub="Registered",
                                                text_entry_format="html"))
        data = self.session.http.json(res)
        return data["item"]

    def _get_media_info(self, content_id):
        """
        Get the info about the content, based on the ID
        :param content_id: contentId for the video
        :return:
        """
        info = self.request('GET', self.stream_url.format(id=content_id))
        return self.request('GET', info.get("playerUrlCallback"))

    def _get_video_id(self):
        #  check the page to find the contentId
        log.debug("Searching for content ID")
        try:
            if self.item_config['type'] == "channel":
                return self._get_live_id()
            else:
                return "vod/{id}".format(id=self.item_config['customFields']['DiceVideoId'])
        except KeyError:
            log.error("Could not find video ID")
            return

    def _get_live_id(self):
        log.debug("Loading live event")
        res = self.request('GET', self.live_url)
        for event in res.get('events', []):
            return "event/{sportId}/{propertyId}/{tournamentId}/{id}".format(**event)

    def _get_streams(self):
        if not self.login(self.get_option("email"), self.get_option("password")):
            raise PluginError("Login failed")

        try:
            start_point = int(float(dict(parse_qsl(urlparse(self.url).query)).get("startPoint", 0.0)))
            if start_point > 0:
                log.info("Stream will start at {0}".format(seconds_to_hhmmss(start_point)))
        except ValueError:
            start_point = 0

        content_id = self._get_video_id()

        if content_id:
            log.debug("Found content ID: {0}".format(content_id))
            info = self._get_media_info(content_id)
            if info.get("hlsUrl"):
                yield from HLSStream.parse_variant_playlist(
                    self.session,
                    info["hlsUrl"],
                    start_offset=start_point
                ).items()
            else:
                log.error("Could not find the HLS URL")


__plugin__ = WWENetwork
