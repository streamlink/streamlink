"""
$description Global live-streaming platform for the creative community.
$url sketch.pixiv.net
$type live
"""

import logging
import re

from streamlink.exceptions import FatalPluginError, NoStreamsError, PluginError
from streamlink.plugin import Plugin, pluginargument, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream


log = logging.getLogger(__name__)


@pluginmatcher(re.compile(
    r"https?://sketch\.pixiv\.net/@?(?P<user>[^/]+)",
))
@pluginargument(
    "sessionid",
    requires=["devicetoken"],
    sensitive=True,
    metavar="SESSIONID",
    help="The pixiv.net sessionid that's used in pixiv's PHPSESSID cookie.",
)
@pluginargument(
    "devicetoken",
    sensitive=True,
    metavar="DEVICETOKEN",
    help="The pixiv.net device token that's used in pixiv's device_token cookie.",
)
@pluginargument(
    "purge-credentials",
    action="store_true",
    help="Purge cached Pixiv credentials to initiate a new session and reauthenticate.",
)
@pluginargument(
    "performer",
    metavar="USER",
    help="Select a co-host stream instead of the owner stream.",
)
class Pixiv(Plugin):
    _post_key_re = re.compile(
        r"""name=["']post_key["']\svalue=["'](?P<data>[^"']+)["']""")

    _user_dict_schema = validate.Schema(
        {
            "user": {
                "unique_name": str,
                "name": str,
            },
            validate.optional("hls_movie"): {
                "url": str,
            },
        },
    )

    _user_schema = validate.Schema(
        {
            "owner": _user_dict_schema,
            "performers": [
                validate.any(_user_dict_schema, None),
            ],
        },
    )

    _data_lives_schema = validate.Schema(
        {
            "data": {
                "lives": [_user_schema],
            },
        },
        validate.get("data"),
        validate.get("lives"),
    )

    api_lives = "https://sketch.pixiv.net/api/lives.json"
    login_url_get = "https://accounts.pixiv.net/login"
    login_url_post = "https://accounts.pixiv.net/api/login"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._authed = (self.session.http.cookies.get("PHPSESSID")
                        and self.session.http.cookies.get("device_token"))
        self.session.http.headers.update({"Referer": self.url})

    def _login_using_session_id_and_device_token(self, session_id, device_token):
        self.session.http.get(self.login_url_get)

        self.session.http.cookies.set("PHPSESSID", session_id, domain=".pixiv.net", path="/")
        self.session.http.cookies.set("device_token", device_token, domain=".pixiv.net", path="/")

        self.save_cookies()
        log.info("Successfully set sessionId and deviceToken")

    def hls_stream(self, hls_url):
        log.debug("URL={0}".format(hls_url))
        yield from HLSStream.parse_variant_playlist(self.session, hls_url).items()

    def get_streamer_data(self):
        headers = {
            "X-Requested-With": "https://sketch.pixiv.net/lives",
        }
        res = self.session.http.get(self.api_lives, headers=headers)
        data = self.session.http.json(res, schema=self._data_lives_schema)
        log.debug("Found {0} streams".format(len(data)))

        for item in data:
            if item["owner"]["user"]["unique_name"] == self.match.group("user"):
                return item

        raise NoStreamsError

    def _get_streams(self):
        login_session_id = self.get_option("sessionid")
        login_device_token = self.get_option("devicetoken")

        if self.options.get("purge_credentials"):
            self.clear_cookies()
            self._authed = False
            log.info("All credentials were successfully removed.")

        if self._authed:
            log.debug("Attempting to authenticate using cached cookies")
        elif login_session_id and login_device_token:
            self._login_using_session_id_and_device_token(login_session_id, login_device_token)

        streamer_data = self.get_streamer_data()
        performers = streamer_data.get("performers")
        log.trace("{0!r}".format(streamer_data))
        if performers:
            co_hosts = [(p["user"]["unique_name"], p["user"]["name"]) for p in performers]
            log.info("Available hosts: {0}".format(", ".join(
                ["{0} ({1})".format(k, v) for k, v in co_hosts])))

            # control if the host from --pixiv-performer is valid,
            # if not let the User select a different host
            if self.get_option("performer") and self.get_option("performer") not in [v[0] for v in co_hosts]:

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
