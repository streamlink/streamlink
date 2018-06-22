from __future__ import print_function

import base64
import logging
import re
from collections import defaultdict
from hashlib import sha1

from streamlink import PluginError
from streamlink.compat import parse_qsl, urlparse
from streamlink.plugin import Plugin, PluginArguments, PluginArgument
from streamlink.plugin.api import http
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
        r'window\.mediatorDefer\s*=\s*page\([^,]*,\s*({.*?})\);', re.DOTALL)
    tvip_re = re.compile(r'channel"\s*:\s*{\s*"id"\s*:\s*"(\w+?)"')
    tvip_master_re = re.compile(r'event_master_brand=(\w+?)&')
    account_locals_re = re.compile(r'window.bbcAccount.locals\s*=\s*({.*?});')
    swf_url = "http://emp.bbci.co.uk/emp/SMPf/1.18.3/StandardMediaPlayerChromelessFlash.swf"
    hash = base64.b64decode(
        b"N2RmZjc2NzFkMGM2OTdmZWRiMWQ5MDVkOWExMjE3MTk5MzhiOTJiZg==")
    api_url = ("http://open.live.bbc.co.uk/mediaselector/6/select/"
               "version/2.0/mediaset/{platform}/vpid/{vpid}/format/json/atk/{vpid_hash}/asn/1/")
    platforms = ("pc", "iptv-all")
    session_url = "https://session.bbc.com/session"
    auth_url = "https://account.bbc.com/signin"

    mediator_schema = validate.Schema(
        {
            "episode": {
                "versions": [{"id": validate.text}]
            }
        },
        validate.get("episode"), validate.get("versions"), validate.get(0),
        validate.get("id")
    )
    mediaselector_schema = validate.Schema(
        validate.transform(parse_json),
        {"media": [
            {"connection": [{
                validate.optional("href"): validate.url(),
                validate.optional("transferFormat"): validate.text
            }],
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
        """ Confirm plugin can handle URL """
        return cls.url_re.match(url) is not None

    @classmethod
    def _hash_vpid(cls, vpid):
        return sha1(cls.hash + str(vpid).encode("utf8")).hexdigest()

    @classmethod
    def _extract_nonce(cls, http_result):
        """
        Given an HTTP response from the sessino endpoint, extract the nonce, so we can "sign" requests with it.
        We don't really sign the requests in the traditional sense of a nonce, we just incude them in the auth requests.

        :param http_result: HTTP response from the bbc session endpoint.
        :type http_result: requests.Response
        :return: nonce to "sign" url requests with
        :rtype: string
        """

        # Extract the redirect URL from the last call
        last_redirect_url = urlparse(http_result.history[-1].request.url)
        last_redirect_query = dict(parse_qsl(last_redirect_url.query))
        # Extract the nonce from the query string in the redirect URL
        final_url = urlparse(last_redirect_query['goto'])
        goto_url = dict(parse_qsl(final_url.query))
        goto_url_query = parse_json(goto_url['state'])

        # Return the nonce we can use for future queries
        return goto_url_query['nonce']

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
        res = res or http.get(url)
        m = self.mediator_re.search(res.text)
        vpid = m and parse_json(m.group(1), schema=self.mediator_schema)
        return vpid

    def find_tvip(self, url, master=False):
        log.debug("Looking for {0} tvip on {1}", "master" if master else "", url)
        res = http.get(url)
        if master:
            m = self.tvip_master_re.search(res.text)
        else:
            m = self.tvip_re.search(res.text)
        return m and m.group(1)

    def mediaselector(self, vpid):
        urls = defaultdict(set)
        for platform in self.platforms:
            url = self.api_url.format(vpid=vpid, vpid_hash=self._hash_vpid(vpid),
                                      platform=platform)
            log.debug("Info API request: {0}", url)
            medias = http.get(url, schema=self.mediaselector_schema)
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
                except:
                    log.debug("  FAIL: {0}", url)

    def login(self, ptrt_url):
        """
        Create session using BBC ID. See https://www.bbc.co.uk/usingthebbc/account/

        :param ptrt_url: The snapback URL to redirect to after successful authentication
        :type ptrt_url: string
        :return: Whether authentication was successful
        :rtype: bool
        """
        session_res = http.get(
            self.session_url,
            params=dict(ptrt=ptrt_url)
        )

        http_nonce = self._extract_nonce(session_res)

        res = http.post(
            self.auth_url,
            params=dict(
                ptrt=ptrt_url,
                nonce=http_nonce
            ),
            data=dict(
                jsEnabled=True,
                username=self.get_option("username"),
                password=self.get_option('password'),
                attempts=0
            ),
            headers={"Referer": self.url})

        return len(res.history) != 0

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
