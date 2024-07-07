"""
$description WNBA - Live Games & Scores.
$url wnba.com
$type  live, vod
$region USA
"""

import logging
import re

from streamlink.plugin import Plugin, PluginError, pluginargument, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://(?:www\.)?leaguepass\.wnba\.com/video/(?P<video_id>\d+)(?:\?|$)",
    ))
@pluginargument(
    "username",
    requires=["password"],
    metavar="USERNAME",
    help="A WNBA username to allow access to restricted streams.",
)
@pluginargument(
    "password",
    sensitive=True,
    metavar="PASSWORD",
    nargs="?",
    const=None,
    default=None,
    help="""
        A WNBA password for use with --crunchyroll-username.

        If left blank you will be prompted.
    """,
)
@pluginargument(
    "purge-credentials",
    action="store_true",
    help="Purge cached Crunchyroll credentials to initiate a new session and reauthenticate.",
)
class WNBA(Plugin):
    _LOGIN_URL = "https://dce-frontoffice.imggaming.com/api/v2/login"
    _TOKEN_API = "https://dce-frontoffice.imggaming.com/api/v1/init/"
    _API_KEY = "857a1e5d-e35e-4fdf-805b-a87b6f8364bf"
    _VOD_API = "https://dce-frontoffice.imggaming.com/api/v4/vod/{id}"
    _headers = {
            "X-Api-Key": _API_KEY,
            "Realm": "dce.wnba",
        }

    def _get_streams(self):
        if self.options.get("purge_credentials"):
            self.cache.set("auth", None, expires=0)

        if not self.options.get("username") and not self.cache.get("auth"):
            log.error("Login needed")
            return

        if self.cache.get("auth"):
            self._headers["Authorization"] = self.cache.get("auth")
        else:
            Authorization = self.session.http.post(self._LOGIN_URL, json={
            "id": self.options.get("username"),
            "secret": self.options.get("password"),
            }, headers=self._headers, schema=validate.Schema(
            validate.parse_json(), {
                validate.optional("messages"): list,
                "authorisationToken": str,
            },
            validate.get("authorisationToken"),
            ))

            self._headers["Authorization"] = f"Mixed {Authorization}"
            self.cache.set("auth", f"Mixed {Authorization}")
            log.info("Session Stored")

        querystring = {
            "lk": "language",
            "pk": ["subTitleLanguage", "audioLanguage", "autoAdvance", "pluginAccessTokens"],
            "readLicences": "true",
            }

        authorisationToken = self.session.http.get(self._TOKEN_API, params=querystring,
                                                   headers=self._headers, schema=validate.Schema(
                                                    validate.parse_json(),
                                                    {
                                                        "authentication": {"authorisationToken": str},
                                                    },
                                                    validate.get("authentication"), validate.get("authorisationToken"),
        ))

        querystring = {"includePlaybackDetails": "URL"}
        self._headers["Authorization"] = f"Bearer {authorisationToken}"

        playerUrlCallback = self.session.http.get(
            self._VOD_API.format(id=self.match.group("video_id")),
            headers=self._headers, params=querystring,
            schema=validate.Schema(
            validate.parse_json(),
            {
                "playerUrlCallback": str,
            },
            validate.get("playerUrlCallback"),
        ))

        hls_url = self.session.http.get(playerUrlCallback, headers=self._headers, schema=validate.Schema(
            validate.parse_json(),
            {
                "hls": [{
                    "url": str,
                }],
            },
            validate.get("hls"), validate.get(0), validate.get("url"),
        ))

        if self.session.http.get(hls_url, raise_for_status=False).status_code != 200:
            log.error("Could not access stream (geo-blocked content, etc.)")
            return

        return HLSStream.parse_variant_playlist(self.session, hls_url)


__plugin__ = WNBA
