
import base64
import logging
import re

from collections import defaultdict
from hashlib import sha1

from streamlink.compat import urlparse
from streamlink.exceptions import PluginError
from streamlink.plugin import Plugin, PluginArguments, PluginArgument
from streamlink.plugin.api import validate
from streamlink.stream import HDSStream
from streamlink.stream import HLSStream
from streamlink.stream.dash import DASHStream
from streamlink.utils import parse_json

log = logging.getLogger(__name__)


class BBCiPlayer(Plugin):
    """
    Allows streaming of live channels from bbc.co.uk/iplayer/live/* and of iPlayer programmes from
    bbc.co.uk/iplayer/episode/*
    """
    url_re = re.compile(r"""https?://(?:www\.)?bbc.co.uk/iplayer/
        (
            episode/(?P<episode_id>\w+)|
            live/(?P<channel_name>\w+)
        )
    """, re.VERBOSE)
    mediator_re = re.compile(
        r'window\.__IPLAYER_REDUX_STATE__\s*=\s*({.*?});', re.DOTALL)
    state_re = re.compile(r'window.__IPLAYER_REDUX_STATE__\s*=\s*({.*});')
    account_locals_re = re.compile(r'window.bbcAccount.locals\s*=\s*({.*?});')
    hash = base64.b64decode(b"N2RmZjc2NzFkMGM2OTdmZWRiMWQ5MDVkOWExMjE3MTk5MzhiOTJiZg==")
    api_url = "https://open.live.bbc.co.uk/mediaselector/6/select/version/2.0/mediaset/{platform}/vpid/{vpid}/format/json/atk/{vpid_hash}/asn/1/"
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
        validate.transform(parse_json),
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
    arguments = PluginArguments(
        PluginArgument(
            "username",
            requires=["password"],
            metavar="USERNAME",
            help="The username used to register with bbc.co.uk."
        ),
        PluginArgument(
            "password",
            sensitive=True,
            metavar="PASSWORD",
            help="A bbc.co.uk account password to use with --bbciplayer-username.",
            prompt="Enter bbc.co.uk account password"
        ),
        PluginArgument(
            "hd",
            action="store_true",
            help="""
            Prefer HD streams over local SD streams, some live programmes may
            not be broadcast in HD.
            """
        ),
    )

    @classmethod
    def can_handle_url(cls, url):
        return cls.url_re.match(url) is not None

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
        log.debug("Looking for vpid on {0}", url)
        # Use pre-fetched page if available
        res = res or self.session.http.get(url)
        m = self.mediator_re.search(res.text)
        vpid = m and parse_json(m.group(1), schema=self.mediator_schema)
        return vpid

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
            log.debug("Info API request: {0}", url)
            medias = self.session.http.get(url, schema=self.mediaselector_schema)
            for media in medias:
                for connection in media["connection"]:
                    urls[connection.get("transferFormat")].add(connection["href"])

        for stream_type, urls in urls.items():
            log.debug("{0} {1} streams", len(urls), stream_type)
            for url in list(urls):
                try:
                    if stream_type == "hds":
                        for s in HDSStream.parse_manifest(self.session,
                                                          url).items():
                            yield s
                    if stream_type == "hls":
                        for s in HLSStream.parse_variant_playlist(self.session,
                                                                  url).items():
                            yield s
                    if stream_type == "dash":
                        for s in DASHStream.parse_manifest(self.session,
                                                           url).items():
                            yield s
                    log.debug("  OK:   {0}", url)
                except Exception:
                    log.debug("  FAIL: {0}", url)

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

        m = self.url_re.match(self.url)
        episode_id = m.group("episode_id")
        channel_name = m.group("channel_name")

        if episode_id:
            log.debug("Loading streams for episode: {0}", episode_id)
            vpid = self.find_vpid(self.url)
            if vpid:
                log.debug("Found VPID: {0}", vpid)
                for s in self.mediaselector(vpid):
                    yield s
            else:
                log.error("Could not find VPID for episode {0}",
                          episode_id)
        elif channel_name:
            log.debug("Loading stream for live channel: {0}", channel_name)
            if self.get_option("hd"):
                tvip = self.find_tvip(self.url, master=True) + "_hd"
                if tvip:
                    log.debug("Trying HD stream {0}...", tvip)
                    try:
                        for s in self.mediaselector(tvip):
                            yield s
                    except PluginError:
                        log.error(
                            "Failed to get HD streams, falling back to SD")
                    else:
                        return
            tvip = self.find_tvip(self.url)
            if tvip:
                log.debug("Found TVIP: {0}", tvip)
                for s in self.mediaselector(tvip):
                    yield s


__plugin__ = BBCiPlayer
