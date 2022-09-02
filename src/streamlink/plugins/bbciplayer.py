"""
$description Live TV channels and video on-demand service from the BBC, a British public, state-owned broadcaster.
$url bbc.co.uk/iplayer
$type live, vod
$region United Kingdom
"""

import base64
import logging
import re
from collections import defaultdict
from hashlib import sha1
from urllib.parse import urlparse, urlunparse

from streamlink.plugin import Plugin, PluginError, pluginargument, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.dash import DASHStream
from streamlink.stream.hls import HLSStream
from streamlink.utils.parse import parse_json

log = logging.getLogger(__name__)


@pluginmatcher(re.compile(r"""
    https?://(?:www\.)?bbc\.co\.uk/iplayer/
    (
        episode/(?P<episode_id>\w+)
        |
        live/(?P<channel_name>\w+)
    )
""", re.VERBOSE))
@pluginargument(
    "username",
    requires=["password"],
    metavar="USERNAME",
    help="The username used to register with bbc.co.uk.",
)
@pluginargument(
    "password",
    prompt="Enter bbc.co.uk account password",
    sensitive=True,
    metavar="PASSWORD",
    help="A bbc.co.uk account password to use with --bbciplayer-username.",
)
@pluginargument(
    "hd",
    action="store_true",
    help="Prefer HD streams over local SD streams, some live programmes may not be broadcast in HD.",
)
class BBCiPlayer(Plugin):
    """
    Allows streaming of live channels from bbc.co.uk/iplayer/live/* and of iPlayer programmes from
    bbc.co.uk/iplayer/episode/*
    """
    mediator_re = re.compile(
        r'window\.__IPLAYER_REDUX_STATE__\s*=\s*({.*?});', re.DOTALL)
    state_re = re.compile(r'window.__IPLAYER_REDUX_STATE__\s*=\s*({.*?});</script>')
    account_locals_re = re.compile(r'window.bbcAccount.locals\s*=\s*({.*?});')
    hash = base64.b64decode(b"N2RmZjc2NzFkMGM2OTdmZWRiMWQ5MDVkOWExMjE3MTk5MzhiOTJiZg==")
    api_url = "https://open.live.bbc.co.uk/mediaselector/6/select/version/2.0/mediaset/" \
              "{platform}/vpid/{vpid}/format/json/atk/{vpid_hash}/asn/1/"
    platforms = ("pc", "iptv-all")
    session_url = "https://session.bbc.com/session"
    auth_url = "https://account.bbc.com/signin"

    mediator_schema = validate.Schema(
        {
            "versions": [{"id": validate.text}]
        },
        validate.get("versions"), validate.get(0),
        validate.get("id")
    )
    mediaselector_schema = validate.Schema(
        validate.parse_json(),
        {"media": [
            {"connection":
                validate.all([{
                    validate.optional("href"): validate.url(),
                    validate.optional("transferFormat"): validate.text
                }], validate.filter(lambda c: c.get("href"))),
                "kind": validate.text}
        ]},
        validate.get("media"),
        validate.filter(lambda x: x["kind"] == "video")
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.url = urlunparse(urlparse(self.url)._replace(scheme="https"))

    @classmethod
    def _hash_vpid(cls, vpid):
        return sha1(cls.hash + str(vpid).encode("utf8")).hexdigest()

    def find_vpid(self, url, res=None):
        """
        Find the Video Packet ID in the HTML for the provided URL

        :param url: URL to download, if res is not provided.
        :param res: Provide a cached version of the HTTP response to search
        :type url: string
        :type res: requests.Response
        :return: Video Packet ID for a Programme in iPlayer
        :rtype: string
        """
        log.debug(f"Looking for vpid on {url}")
        # Use pre-fetched page if available
        res = res or self.session.http.get(url)
        m = self.mediator_re.search(res.text)
        return m and parse_json(m.group(1), schema=self.mediator_schema)

    def find_tvip(self, url, master=False):
        log.debug("Looking for {0} tvip on {1}".format("master" if master else "", url))
        res = self.session.http.get(url)
        m = self.state_re.search(res.text)
        data = m and parse_json(m.group(1))
        if data:
            channel = data.get("channel")
            if master:
                return channel.get("masterBrand")
            return channel.get("id")

    def mediaselector(self, vpid):
        urls = defaultdict(set)
        for platform in self.platforms:
            url = self.api_url.format(vpid=vpid, vpid_hash=self._hash_vpid(vpid),
                                      platform=platform)
            log.debug(f"Info API request: {url}")
            medias = self.session.http.get(url, schema=self.mediaselector_schema)
            for media in medias:
                for connection in media["connection"]:
                    urls[connection.get("transferFormat")].add(connection["href"])

        for stream_type, urls in urls.items():
            log.debug(f"{len(urls)} {stream_type} streams")
            for url in list(urls):
                try:
                    if stream_type == "hls":
                        yield from HLSStream.parse_variant_playlist(self.session, url).items()
                    if stream_type == "dash":
                        yield from DASHStream.parse_manifest(self.session, url).items()
                    log.debug(f"  OK:   {url}")
                except Exception:
                    log.debug(f"  FAIL: {url}")

    def login(self, ptrt_url):
        """
        Create session using BBC ID. See https://www.bbc.co.uk/usingthebbc/account/

        :param ptrt_url: The snapback URL to redirect to after successful authentication
        :type ptrt_url: string
        :return: Whether authentication was successful
        :rtype: bool
        """

        def auth_check(res):
            return ptrt_url in ([h.url for h in res.history] + [res.url])

        # make the session request to get the correct cookies
        session_res = self.session.http.get(
            self.session_url,
            params=dict(ptrt=ptrt_url)
        )

        if auth_check(session_res):
            log.debug("Already authenticated, skipping authentication")
            return True

        res = self.session.http.post(
            self.auth_url,
            params=urlparse(session_res.url).query,
            data=dict(
                jsEnabled=True,
                username=self.get_option("username"),
                password=self.get_option('password'),
                attempts=0
            ),
            headers={"Referer": self.url})

        return auth_check(res)

    def _get_streams(self):
        if not self.get_option("username"):
            log.error(
                "BBC iPlayer requires an account you must login using "
                "--bbciplayer-username and --bbciplayer-password")
            return
        log.info(
            "A TV License is required to watch BBC iPlayer streams, see the BBC website for more "
            "information: https://www.bbc.co.uk/iplayer/help/tvlicence")
        if not self.login(self.url):
            log.error(
                "Could not authenticate, check your username and password")
            return

        episode_id = self.match.group("episode_id")
        channel_name = self.match.group("channel_name")

        if episode_id:
            log.debug(f"Loading streams for episode: {episode_id}")
            vpid = self.find_vpid(self.url)
            if vpid:
                log.debug(f"Found VPID: {vpid}")
                yield from self.mediaselector(vpid)
            else:
                log.error(f"Could not find VPID for episode {episode_id}")
        elif channel_name:
            log.debug(f"Loading stream for live channel: {channel_name}")
            if self.get_option("hd"):
                tvip = f"{self.find_tvip(self.url, master=True)}_hd"
                if tvip:
                    log.debug(f"Trying HD stream {tvip}...")
                    try:
                        yield from self.mediaselector(tvip)
                    except PluginError:
                        log.error("Failed to get HD streams, falling back to SD")
                    else:
                        return
            tvip = self.find_tvip(self.url)
            if tvip:
                log.debug(f"Found TVIP: {tvip}")
                yield from self.mediaselector(tvip)


__plugin__ = BBCiPlayer
