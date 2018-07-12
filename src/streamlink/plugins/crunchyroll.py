import argparse
import datetime
import random
import re
import string
import logging
from uuid import uuid4

from streamlink.plugin import Plugin, PluginError, PluginArguments, PluginArgument
from streamlink.plugin.api import http, validate, useragents
from streamlink.stream import HLSStream

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
        datetime.datetime.strptime(ts[:-7], "%Y-%m-%dT%H:%M:%S") +
        datetime.timedelta(hours=int(ts[-5:-3]), minutes=int(ts[-2:])) *
        int(ts[-6:-5] + "1")
    )


_url_re = re.compile(r"""
    http(s)?://(\w+\.)?crunchyroll\.
    (?:
        com|de|es|fr|co.jp
    )
    (?:/[^/&?]+)?
    /[^/&?]+-(?P<media_id>\d+)
""", re.VERBOSE)

_api_schema = validate.Schema({
    "error": bool,
    validate.optional("code"): validate.text,
    validate.optional("message"): validate.text,
    validate.optional("data"): object,
})
_media_schema = validate.Schema(
    {
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
    },
    validate.get("stream_data")
)
_login_schema = validate.Schema({
    "auth": validate.text,
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


class CrunchyrollAPI(object):
    _api_url = "https://api.crunchyroll.com/{0}.0.json"
    _default_locale = "en_US"
    _user_agent = "Dalvik/1.6.0 (Linux; U; Android 4.4.2; Android SDK built for x86 Build/KK)"
    _version_code = 444
    _version_name = "2.1.10"
    _access_token = "Scwg9PRRZ19iVwD"
    _access_type = "com.crunchyroll.crunchyroid"

    def __init__(self, cache, session_id=None, locale=_default_locale):
        """Abstract the API to access to Crunchyroll data.

        Can take saved credentials to use on it's calls to the API.
        """
        self.cache = cache
        self.session_id = session_id
        if self.session_id:  # if the session ID is setup don't use the cached auth token
            self.auth = None
        else:
            self.auth = cache.get("auth")
        self.device_id = cache.get("device_id") or self.generate_device_id()
        self.locale = locale
        self.headers = {
            "X-Android-Device-Is-GoogleTV": "0",
            "X-Android-Device-Product": "google_sdk_x86",
            "X-Android-Device-Model": "Android SDK built for x86",
            "Using-Brightcove-Player": "1",
            "X-Android-Release": "4.4.2",
            "X-Android-SDK": "19",
            "X-Android-Application-Version-Name": self._version_name,
            "X-Android-Application-Version-Code": str(self._version_code),
            'User-Agent': self._user_agent
        }

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
                "version": self._version_code
            })
        params.update({
            "locale": self.locale.replace('_', ''),
        })

        if self.session_id:
            params["session_id"] = self.session_id

        # The certificate used by Crunchyroll cannot be verified in some environments.
        res = http.post(url, data=params, headers=self.headers, verify=False)
        json_res = http.json(res, schema=_api_schema)

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
        self.cache.set("device_id", 365 * 24 * 60 * 60)
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
        data = self._api_call("authenticate", {"auth": self.auth}, schema=_login_schema)
        self.auth = data["auth"]
        self.cache.set("auth", data["auth"], expires_at=data["expires"])
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


class Crunchyroll(Plugin):
    arguments = PluginArguments(
        PluginArgument(
            "username",
            metavar="USERNAME",
            requires=["password"],
            help="A Crunchyroll username to allow access to restricted streams."
        ),
        PluginArgument(
            "password",
            sensitive=True,
            metavar="PASSWORD",
            nargs="?",
            const=None,
            default=None,
            help="""
            A Crunchyroll password for use with --crunchyroll-username.

            If left blank you will be prompted.
            """
        ),
        PluginArgument(
            "purge-credentials",
            action="store_true",
            help="""
            Purge cached Crunchyroll credentials to initiate a new session
            and reauthenticate.
            """
        ),
        PluginArgument(
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
            """
        ),
        # Deprecated, uses the general locale setting
        PluginArgument(
            "locale",
            metavar="LOCALE",
            help=argparse.SUPPRESS
        )
    )

    @classmethod
    def can_handle_url(self, url):
        return _url_re.match(url)

    @classmethod
    def stream_weight(cls, key):
        weight = STREAM_WEIGHTS.get(key)
        if weight:
            return weight, "crunchyroll"

        return Plugin.stream_weight(key)

    def _get_streams(self):
        api = self._create_api()
        match = _url_re.match(self.url)
        media_id = int(match.group("media_id"))

        try:
            # the media.stream_data field is required, no stream data is returned otherwise
            info = api.get_info(media_id, fields=["media.stream_data"], schema=_media_schema)
        except CrunchyrollAPIError as err:
            raise PluginError(u"Media lookup error: {0}".format(err.msg))

        if not info:
            return

        streams = {}

        # The adaptive quality stream sometimes a subset of all the other streams listed, ultra is no included
        has_adaptive = any([s[u"quality"] == u"adaptive" for s in info[u"streams"]])
        if has_adaptive:
            self.logger.debug(u"Loading streams from adaptive playlist")
            for stream in filter(lambda x: x[u"quality"] == u"adaptive", info[u"streams"]):
                for q, s in HLSStream.parse_variant_playlist(self.session, stream[u"url"]).items():
                    # rename the bitrates to low, mid, or high. ultra doesn't seem to appear in the adaptive streams
                    name = STREAM_NAMES.get(q, q)
                    streams[name] = s

        # If there is no adaptive quality stream then parse each individual result
        for stream in info[u"streams"]:
            if stream[u"quality"] != u"adaptive":
                # the video_encode_id indicates that the stream is not a variant playlist
                if u"video_encode_id" in stream:
                    streams[stream[u"quality"]] = HLSStream(self.session, stream[u"url"])
                else:
                    # otherwise the stream url is actually a list of stream qualities
                    for q, s in HLSStream.parse_variant_playlist(self.session, stream[u"url"]).items():
                        # rename the bitrates to low, mid, or high. ultra doesn't seem to appear in the adaptive streams
                        name = STREAM_NAMES.get(q, q)
                        streams[name] = s

        return streams

    def _create_api(self):
        """Creates a new CrunchyrollAPI object, initiates it's session and
        tries to authenticate it either by using saved credentials or the
        user's username and password.
        """
        if self.options.get("purge_credentials"):
            self.cache.set("session_id", None, 0)
            self.cache.set("auth", None, 0)
            self.cache.set("session_id", None, 0)

        # use the crunchyroll locale as an override, for backwards compatibility
        locale = self.get_option("locale") or self.session.localization.language_code
        api = CrunchyrollAPI(self.cache, session_id=self.get_option("session_id"), locale=locale)

        if not self.get_option("session_id"):
            self.logger.debug("Creating session with locale: {0}", locale)
            api.start_session()

            if api.auth:
                self.logger.debug("Using saved credentials")
                login = api.authenticate()
                self.logger.info("Successfully logged in as '{0}'",
                                 login["user"]["username"] or login["user"]["email"])
            elif self.options.get("username"):
                try:
                    self.logger.debug("Attempting to login using username and password")
                    api.login(self.options.get("username"),
                              self.options.get("password"))
                    login = api.authenticate()
                    self.logger.info("Logged in as '{0}'",
                                     login["user"]["username"] or login["user"]["email"])

                except CrunchyrollAPIError as err:
                    raise PluginError(u"Authentication error: {0}".format(err.msg))
            else:
                self.logger.warning(
                    "No authentication provided, you won't be able to access "
                    "premium restricted content"
                )

        return api


__plugin__ = Crunchyroll
