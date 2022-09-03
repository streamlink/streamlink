"""
$description Video streaming service focused on anime, manga, and dorama.
$url crunchyroll.com
$type vod
"""

import datetime
import logging
import re
from uuid import uuid4

from streamlink.plugin import Plugin, PluginError, pluginargument, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream

log = logging.getLogger(__name__)

STREAM_WEIGHTS = {
    "low": 240,
    "mid": 420,
    "high": 720,
    "ultra": 1080,
}
STREAM_NAMES = {
    "120k": "low",
    "328k": "mid",
    "864k": "high"
}


def parse_timestamp(ts):
    """Takes ISO 8601 format(string) and converts into a utc datetime(naive)"""
    return (
        datetime.datetime.strptime(ts[:-7], "%Y-%m-%dT%H:%M:%S")
        + datetime.timedelta(hours=int(ts[-5:-3]), minutes=int(ts[-2:]))
        * int(f"{ts[-6:-5]}1")
    )


_api_schema = validate.Schema({
    "error": bool,
    validate.optional("code"): validate.text,
    validate.optional("message"): validate.text,
    validate.optional("data"): object,
})
_media_schema = validate.Schema(
    {
        validate.optional("name"): validate.any(validate.text, None),
        validate.optional("series_name"): validate.any(validate.text, None),
        validate.optional("media_type"): validate.any(validate.text, None),
        "stream_data": validate.any(
            None,
            {
                "streams": validate.all(
                    [{
                        "quality": validate.any(validate.text, None),
                        "url": validate.url(
                            scheme="http",
                            path=validate.endswith(".m3u8")
                        ),
                        validate.optional("video_encode_id"): validate.text
                    }]
                )
            }
        )
    }
)
_login_schema = validate.Schema({
    "auth": validate.any(validate.text, None),
    "expires": validate.all(
        validate.text,
        validate.transform(parse_timestamp)
    ),
    "user": {
        "username": validate.any(validate.text, None),
        "email": validate.text
    }
})
_session_schema = validate.Schema(
    {
        "session_id": validate.text
    },
    validate.get("session_id")
)


class CrunchyrollAPIError(Exception):
    """Exception thrown by the Crunchyroll API when an error occurs"""

    def __init__(self, msg, code):
        Exception.__init__(self, msg)
        self.msg = msg
        self.code = code


class CrunchyrollAPI:
    _api_url = "https://api.crunchyroll.com/{0}.0.json"
    _default_locale = "en_US"
    _version_name = "1.3.1.0"
    _access_token = "LNDJgOit5yaRIWN"
    _access_type = "com.crunchyroll.windows.desktop"

    def __init__(self, cache, session, session_id=None, locale=_default_locale):
        """Abstract the API to access to Crunchyroll data.

        Can take saved credentials to use on its calls to the API.
        """
        self.cache = cache
        self.session = session
        self.session_id = session_id
        if self.session_id:  # if the session ID is setup don't use the cached auth token
            self.auth = None
        else:
            self.auth = cache.get("auth")
        self.device_id = cache.get("device_id") or self.generate_device_id()
        self.locale = locale

    def _api_call(self, entrypoint, params=None, schema=None):
        """Makes a call against the api.

        :param entrypoint: API method to call.
        :param params: parameters to include in the request data.
        :param schema: schema to use to validate the data
        """
        url = self._api_url.format(entrypoint)

        # Default params
        params = params or {}
        if self.session_id:
            params.update({
                "session_id": self.session_id
            })
        else:
            params.update({
                "device_id": self.device_id,
                "device_type": self._access_type,
                "access_token": self._access_token,
            })
        params.update({
            "locale": self.locale.replace("_", ""),
            "version": self._version_name,
            "connectivity_type": "ethernet",
        })

        if self.session_id:
            params["session_id"] = self.session_id

        res = self.session.http.post(url, data=params)
        json_res = self.session.http.json(res, schema=_api_schema)

        if json_res["error"]:
            err_msg = json_res.get("message", "Unknown error")
            err_code = json_res.get("code", "unknown_error")
            raise CrunchyrollAPIError(err_msg, err_code)

        data = json_res.get("data")
        if schema:
            data = schema.validate(data, name="API response")

        return data

    def generate_device_id(self):
        device_id = str(uuid4())
        # cache the device id
        self.cache.set("device_id", device_id, expires=365 * 24 * 60 * 60)
        log.debug("Device ID: {0}".format(device_id))
        return device_id

    def start_session(self):
        """
            Starts a session against Crunchyroll's server.
            Is recommended that you call this method before making any other calls
            to make sure you have a valid session against the server.
        """
        params = {}
        if self.auth:
            params["auth"] = self.auth
        self.session_id = self._api_call("start_session", params, schema=_session_schema)
        log.debug("Session created with ID: {0}".format(self.session_id))
        return self.session_id

    def login(self, username, password):
        """
            Authenticates the session to be able to access restricted data from
            the server (e.g. premium restricted videos).
        """
        params = {
            "account": username,
            "password": password
        }

        login = self._api_call("login", params, schema=_login_schema)
        self.auth = login["auth"]
        self.cache.set("auth", login["auth"], expires_at=login["expires"])
        return login

    def authenticate(self):
        try:
            data = self._api_call("authenticate", {"auth": self.auth}, schema=_login_schema)
        except CrunchyrollAPIError:
            self.auth = None
            self.cache.set("auth", None, expires=0)
            log.warning("Saved credentials have expired")
            return

        log.debug("Credentials expire at: {}".format(data["expires"]))
        self.cache.set("auth", self.auth, expires_at=data["expires"])
        return data

    def get_info(self, media_id, fields=None, schema=None):
        """
            Returns the data for a certain media item.

            :param media_id: id that identifies the media item to be accessed.
            :param fields: list of the media"s field to be returned. By default the
            API returns some fields, but others are not returned unless they are
            explicity asked for. I have no real documentation on the fields, but
            they all seem to start with the "media." prefix (e.g. media.name,
            media.stream_data).
            :param schema: validation schema to use
        """
        params = {"media_id": media_id}

        if fields:
            params["fields"] = ",".join(fields)

        return self._api_call("info", params, schema=schema)


@pluginmatcher(re.compile(r"""
    https?://(\w+\.)?crunchyroll\.
    (?:
        com|de|es|fr|co\.jp
    )
    (?:
        /(en-gb|es|es-es|pt-pt|pt-br|fr|de|ar|it|ru)
    )?
    (?:
        (?:
            (?:/[^/&?]+)?
            /[^/&?]+-(?P<media_id>\d+)
        )
        |
        /watch/(?P<beta_id>\w+)/[\w-]+
    )
""", re.VERBOSE))
@pluginargument(
    "username",
    requires=["password"],
    metavar="USERNAME",
    help="A Crunchyroll username to allow access to restricted streams.",
)
@pluginargument(
    "password",
    sensitive=True,
    metavar="PASSWORD",
    nargs="?",
    const=None,
    default=None,
    help="""
        A Crunchyroll password for use with --crunchyroll-username.

        If left blank you will be prompted.
    """,
)
@pluginargument(
    "purge-credentials",
    action="store_true",
    help="Purge cached Crunchyroll credentials to initiate a new session and reauthenticate.",
)
@pluginargument(
    "session-id",
    sensitive=True,
    metavar="SESSION_ID",
    help="""
        Set a specific session ID for crunchyroll, can be used to bypass
        region restrictions. If using an authenticated session ID, it is
        recommended that the authentication parameters be omitted as the
        session ID is account specific.

        Note: The session ID will be overwritten if authentication is used
        and the session ID does not match the account.
    """,
)
class Crunchyroll(Plugin):
    @classmethod
    def stream_weight(cls, key):
        weight = STREAM_WEIGHTS.get(key)
        if weight:
            return weight, "crunchyroll"

        return Plugin.stream_weight(key)

    def _get_streams(self):
        beta_id = self.match.group("beta_id")
        if beta_id:
            json = self.session.http.get(self.url, schema=validate.Schema(
                validate.parse_html(),
                validate.xml_xpath_string(".//script[contains(text(), 'window.__INITIAL_STATE__')]/text()"),
                validate.none_or_all(
                    re.compile(r"window.__INITIAL_STATE__\s*=\s*({.*});"),
                    validate.none_or_all(
                        validate.get(1),
                        validate.parse_json(),
                        validate.none_or_all(
                            {"content": {"byId": {str: {"external_id": validate.all(
                                validate.transform(lambda s: int(s.replace("EPI.", ""))),
                            )}}}},
                            validate.get(("content", "byId")),
                        ),
                    ),
                ),
            ))
            if not json or beta_id not in json:
                return
            media_id = json[beta_id]["external_id"]
        else:
            media_id = int(self.match.group("media_id"))

        api = self._create_api()
        try:
            # the media.stream_data field is required, no stream data is returned otherwise
            info = api.get_info(media_id, fields=["media.name", "media.series_name",
                                "media.media_type", "media.stream_data"], schema=_media_schema)
        except CrunchyrollAPIError as err:
            raise PluginError(f"Media lookup error: {err.msg}")

        if not info:
            return

        streams = {}

        self.id = media_id
        self.title = info.get("name")
        self.author = info.get("series_name")
        self.category = info.get("media_type")

        info = info["stream_data"]

        # The adaptive quality stream sometimes a subset of all the other streams listed, ultra is no included
        has_adaptive = any(s["quality"] == "adaptive" for s in info["streams"])
        if has_adaptive:
            log.debug("Loading streams from adaptive playlist")
            for stream in filter(lambda x: x["quality"] == "adaptive", info["streams"]):
                for q, s in HLSStream.parse_variant_playlist(self.session, stream["url"]).items():
                    # rename the bitrates to low, mid, or high. ultra doesn't seem to appear in the adaptive streams
                    name = STREAM_NAMES.get(q, q)
                    streams[name] = s

        # If there is no adaptive quality stream then parse each individual result
        for stream in info["streams"]:
            if stream["quality"] != "adaptive":
                # the video_encode_id indicates that the stream is not a variant playlist
                if "video_encode_id" in stream:
                    streams[stream["quality"]] = HLSStream(self.session, stream["url"])
                else:
                    # otherwise the stream url is actually a list of stream qualities
                    for q, s in HLSStream.parse_variant_playlist(self.session, stream["url"]).items():
                        # rename the bitrates to low, mid, or high. ultra doesn't seem to appear in the adaptive streams
                        name = STREAM_NAMES.get(q, q)
                        streams[name] = s

        return streams

    def _create_api(self):
        """Creates a new CrunchyrollAPI object, initiates its session and
        tries to authenticate it either by using saved credentials or the
        user's username and password.
        """
        if self.options.get("purge_credentials"):
            self.cache.set("device_id", None, expires=0)
            self.cache.set("auth", None, expires=0)

        # use the crunchyroll locale as an override, for backwards compatibility
        locale = self.get_option("locale") or self.session.localization.language_code
        api = CrunchyrollAPI(self.cache,
                             self.session,
                             session_id=self.get_option("session_id"),
                             locale=locale)

        if not self.get_option("session_id"):
            log.debug(f"Creating session with locale: {locale}")
            api.start_session()

            if api.auth:
                log.debug("Using saved credentials")
                login = api.authenticate()
                if login:
                    login_name = login["user"]["username"] or login["user"]["email"]
                    log.info(f"Successfully logged in as '{login_name}'")
            if not api.auth and self.options.get("username"):
                try:
                    log.debug("Attempting to login using username and password")
                    api.login(self.options.get("username"),
                              self.options.get("password"))
                    login = api.authenticate()
                    login_name = login["user"]["username"] or login["user"]["email"]
                    log.info(f"Logged in as '{login_name}'")

                except CrunchyrollAPIError as err:
                    raise PluginError(f"Authentication error: {err.msg}")
            if not api.auth:
                log.warning(
                    "No authentication provided, you won't be able to access "
                    "premium restricted content"
                )

        return api


__plugin__ = Crunchyroll
