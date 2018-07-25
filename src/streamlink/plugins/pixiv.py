# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import re

from streamlink.exceptions import FatalPluginError, NoStreamsError, PluginError
from streamlink.plugin import Plugin, PluginArguments, PluginArgument
from streamlink.plugin.api import useragents, validate
from streamlink.stream import HLSStream
from streamlink.utils.encoding import maybe_decode

log = logging.getLogger(__name__)


class Pixiv(Plugin):
    """Plugin for https://sketch.pixiv.net/lives"""

    _url_re = re.compile(r"https?://sketch\.pixiv\.net/@?(?P<user>[^/]+)")
    _post_key_re = re.compile(
        r"""name=["']post_key["']\svalue=["'](?P<data>[^"']+)["']""")

    _user_dict_schema = validate.Schema(
        {
            "user": {
                "unique_name": validate.text,
                "name": validate.all(validate.text,
                                     validate.transform(maybe_decode))
            },
            validate.optional("hls_movie"): {
                "url": validate.text
            }
        }
    )

    _user_schema = validate.Schema(
        {
            "owner": _user_dict_schema,
            "performers": [
                validate.any(_user_dict_schema, None)
            ]
        }
    )

    _data_lives_schema = validate.Schema(
        {
            "data": {
                "lives": [_user_schema]
            }
        },
        validate.get("data"),
        validate.get("lives")
    )

    api_lives = "https://sketch.pixiv.net/api/lives.json"
    login_url_get = "https://accounts.pixiv.net/login"
    login_url_post = "https://accounts.pixiv.net/api/login"

    arguments = PluginArguments(
        PluginArgument(
            "username",
            requires=["password"],
            metavar="USERNAME",
            help="""
        The email/username used to register with pixiv.net
        """
        ),
        PluginArgument(
            "password",
            sensitive=True,
            metavar="PASSWORD",
            help="""
        A pixiv.net account password to use with --pixiv-username
        """
        ),
        PluginArgument(
            "purge-credentials",
            action="store_true",
            help="""
        Purge cached Pixiv credentials to initiate a new session
        and reauthenticate.
        """),
        PluginArgument(
            "performer",
            metavar="USER",
            help="""
        Select a co-host stream instead of the owner stream.
        """)
    )

    def __init__(self, url):
        super(Pixiv, self).__init__(url)
        self._authed = (self.session.http.cookies.get("PHPSESSID")
                        and self.session.http.cookies.get("device_token"))
        self.session.http.headers.update({
            "User-Agent": useragents.FIREFOX,
            "Referer": self.url
        })

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url) is not None

    def _login(self, username, password):
        res = self.session.http.get(self.login_url_get)
        m = self._post_key_re.search(res.text)
        if not m:
            raise PluginError("Missing post_key, no login posible.")

        post_key = m.group("data")
        data = {
            "lang": "en",
            "source": "sketch",
            "post_key": post_key,
            "pixiv_id": username,
            "password": password,
        }

        res = self.session.http.post(self.login_url_post, data=data)
        res = self.session.http.json(res)
        log.trace("{0!r}".format(res))
        if res["body"].get("success"):
            self.save_cookies()
            log.info("Successfully logged in")
        else:
            log.error("Failed to log in.")

    def hls_stream(self, hls_url):
        log.debug("URL={0}".format(hls_url))
        for s in HLSStream.parse_variant_playlist(self.session, hls_url).items():
            yield s

    def get_streamer_data(self):
        res = self.session.http.get(self.api_lives)
        data = self.session.http.json(res, schema=self._data_lives_schema)
        log.debug("Found {0} streams".format(len(data)))

        m = self._url_re.match(self.url)
        for item in data:
            if item["owner"]["user"]["unique_name"] == m.group("user"):
                return item

        raise NoStreamsError(self.url)

    def _get_streams(self):
        login_username = self.get_option("username")
        login_password = self.get_option("password")

        if self.options.get("purge_credentials"):
            self.clear_cookies()
            self._authed = False
            log.info("All credentials were successfully removed.")

        if self._authed:
            log.debug("Attempting to authenticate using cached cookies")
        elif not self._authed and login_username and login_password:
            self._login(login_username, login_password)

        streamer_data = self.get_streamer_data()
        performers = streamer_data.get("performers")
        log.trace("{0!r}".format(streamer_data))
        if performers:
            co_hosts = []
            # create a list of all available performers
            for p in performers:
                co_hosts += [(p["user"]["unique_name"], p["user"]["name"])]

            log.info("Available hosts: {0}".format(", ".join(
                ["{0} ({1})".format(k, v) for k, v in co_hosts])))

            # control if the host from --pixiv-performer is valid,
            # if not let the User select a different host
            if (self.get_option("performer")
                    and not self.get_option("performer") in [v[0] for v in co_hosts]):

                # print the owner as 0
                log.info("0 - {0} ({1})".format(
                    streamer_data["owner"]["user"]["unique_name"],
                    streamer_data["owner"]["user"]["name"]))
                # print all other performer
                for i, item in enumerate(co_hosts, start=1):
                    log.info("{0} - {1} ({2})".format(i, item[0], item[1]))

                try:
                    number = int(self.input_ask(
                        "Enter the number you'd like to watch").split(" ")[0])
                    if number == 0:
                        # default stream
                        self.set_option("performer", None)
                    else:
                        # other co-hosts
                        self.set_option("performer", co_hosts[number - 1][0])
                except FatalPluginError:
                    raise PluginError("Selected performer is invalid.")
                except (IndexError, ValueError, TypeError):
                    raise PluginError("Input is invalid")

        # ignore the owner stream, if a performer is selected
        # or use it when there are no other performers
        if not self.get_option("performer") or not performers:
            return self.hls_stream(streamer_data["owner"]["hls_movie"]["url"])

        # play a co-host stream
        if performers and self.get_option("performer"):
            for p in performers:
                if p["user"]["unique_name"] == self.get_option("performer"):
                    # if someone goes online at the same time as Streamlink
                    # was used, the hls URL might not be in the JSON data
                    hls_movie = p.get("hls_movie")
                    if hls_movie:
                        return self.hls_stream(hls_movie["url"])


__plugin__ = Pixiv
