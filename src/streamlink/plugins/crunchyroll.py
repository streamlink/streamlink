import random
import re
import string
import datetime

from streamlink.plugin import Plugin, PluginError, PluginOptions
from streamlink.plugin.api import http, validate
from streamlink.stream import HLSStream

API_URL = "https://api.crunchyroll.com/{0}.0.json"
API_DEFAULT_LOCALE = "en_US"
API_USER_AGENT = "Mozilla/5.0 (iPhone; iPhone OS 8.3.0; {})"
API_HEADERS = {
    "Host": "api.crunchyroll.com",
    "Accept-Encoding": "gzip, deflate",
    "Accept": "*/*",
    "Content-Type": "application/x-www-form-urlencoded"
}
API_VERSION = "2313.8"
API_ACCESS_TOKEN = "QWjz212GspMHH9h"
API_DEVICE_TYPE = "com.crunchyroll.iphone"
STREAM_WEIGHTS = {
    "low": 240,
    "mid": 420,
    "high": 720,
    "ultra": 1080,
}


def parse_timestamp(ts):
    """Takes ISO 8601 format(string) and converts into a utc datetime(naive)"""
    return (
        datetime.datetime.strptime(ts[:-7], "%Y-%m-%dT%H:%M:%S") +
        datetime.timedelta(hours=int(ts[-5:-3]), minutes=int(ts[-2:])) *
        int(ts[-6:-5] + "1")
    )


_url_re = re.compile("""
    http(s)?://(\w+\.)?crunchyroll\.
    (?:
        com|de|es|fr|co.jp
    )
    /[^/&?]+
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
                        )
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
        "username": validate.text
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
    def __init__(self, session_id=None, auth=None, locale=API_DEFAULT_LOCALE):
        """Abstract the API to access to Crunchyroll data.

        Can take saved credentials to use on it's calls to the API.
        """
        self.session_id = session_id
        self.auth = auth
        self.locale = locale

    def _api_call(self, entrypoint, params, schema=None):
        """Makes a call against the api.

        :param entrypoint: API method to call.
        :param params: parameters to include in the request data.
        :param schema: schema to use to validate the data
        """
        url = API_URL.format(entrypoint)

        # Default params
        params = dict(params)
        params.update({
            "version": API_VERSION,
            "locale": self.locale.replace('_', ''),
        })

        if self.session_id:
            params["session_id"] = self.session_id

        # Headers
        headers = dict(API_HEADERS)
        headers['User-Agent'] = API_USER_AGENT.format(self.locale)

        # The certificate used by Crunchyroll cannot be verified in some environments.
        res = http.get(url, params=params, headers=headers, verify=False)
        json_res = http.json(res, schema=_api_schema)

        if json_res["error"]:
            err_msg = json_res.get("message", "Unknown error")
            err_code = json_res.get("code", "unknown_error")
            raise CrunchyrollAPIError(err_msg, err_code)

        data = json_res.get("data")
        if schema:
            data = schema.validate(data, name="API response")

        return data

    def start_session(self, device_id, **kwargs):
        """Starts a session against Crunchyroll's server.

        Is recommended that you call this method before making any other calls
        to make sure you have a valid session against the server.
        """
        params = {
            "device_id": device_id,
            "device_type": API_DEVICE_TYPE,
            "access_token": API_ACCESS_TOKEN,
        }

        if self.auth:
            params["auth"] = self.auth

        return self._api_call("start_session", params, **kwargs)

    def login(self, username, password, **kwargs):
        """Authenticates the session to be able to access restricted data from
        the server (e.g. premium restricted videos).
        """
        params = {
            "account": username,
            "password": password
        }

        return self._api_call("login", params, **kwargs)

    def get_info(self, media_id, fields=None, **kwargs):
        """Returns the data for a certain media item.

        :param media_id: id that identifies the media item to be accessed.
        :param fields: list of the media"s field to be returned. By default the
        API returns some fields, but others are not returned unless they are
        explicity asked for. I have no real documentation on the fields, but
        they all seem to start with the "media." prefix (e.g. media.name,
        media.stream_data).
        """
        params = {
            "media_id": media_id
        }

        if fields:
            params["fields"] = ",".join(fields)

        return self._api_call("info", params, **kwargs)


class Crunchyroll(Plugin):
    options = PluginOptions({
        "username": None,
        "password": None,
        "purge_credentials": None,
        "locale": API_DEFAULT_LOCALE
    })

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
            info = api.get_info(media_id, fields=["media.stream_data"],
                                schema=_media_schema)
        except CrunchyrollAPIError as err:
            raise PluginError(u"Media lookup error: {0}".format(err.msg))

        if not info:
            return

        # The adaptive quality stream contains a superset of all the other streams listeed
        has_adaptive = any([s[u"quality"] == u"adaptive" for s in info[u"streams"]])
        if has_adaptive:
            self.logger.debug(u"Loading streams from adaptive playlist")
            for stream in filter(lambda x: x[u"quality"] == u"adaptive", info[u"streams"]):
                return HLSStream.parse_variant_playlist(self.session, stream["url"])
        else:
            streams = {}
            # If there is no adaptive quality stream then parse each individual result
            for stream in info[u"streams"]:
                # the video_encode_id indicates that the stream is not a variant playlist
                if u"video_encode_id" in stream:
                    streams[stream[u"quality"]] = HLSStream(self.session, stream[u"url"])
                else:
                    # otherwise the stream url is actually a list of stream qualities
                    streams.update(HLSStream.parse_variant_playlist(self.session, stream[u"url"]))

            return streams

    def _get_device_id(self):
        """Returns the saved device id or creates a new one and saves it."""
        device_id = self.cache.get("device_id")

        if not device_id:
            # Create a random device id and cache it for a year
            char_set = string.ascii_letters + string.digits
            device_id = "".join(random.sample(char_set, 32))
            self.cache.set("device_id", device_id, 365 * 24 * 60 * 60)

        return device_id

    def _create_api(self):
        """Creates a new CrunchyrollAPI object, initiates it's session and
        tries to authenticate it either by using saved credentials or the
        user's username and password.
        """
        if self.options.get("purge_credentials"):
            self.cache.set("session_id", None, 0)
            self.cache.set("auth", None, 0)

        current_time = datetime.datetime.utcnow()
        device_id = self._get_device_id()
        locale = self.options.get("locale")
        api = CrunchyrollAPI(
            self.cache.get("session_id"), self.cache.get("auth"), locale
        )

        self.logger.debug("Creating session")
        try:
            api.session_id = api.start_session(device_id, schema=_session_schema)
        except CrunchyrollAPIError as err:
            if err.code == "bad_session":
                self.logger.debug("Current session has expired, creating a new one")
                api = CrunchyrollAPI(locale=locale)
                api.session_id = api.start_session(device_id, schema=_session_schema)
            else:
                raise err

        # Save session and hope it lasts for a few hours
        self.cache.set("session_id", api.session_id, 4 * 60 * 60)
        self.logger.debug("Session created")

        if api.auth:
            self.logger.debug("Using saved credentials")
        elif self.options.get("username"):
            try:
                self.logger.info("Attempting to login using username and password")
                login = api.login(
                    self.options.get("username"),
                    self.options.get("password"),
                    schema=_login_schema
                )
                api.auth = login["auth"]

                self.logger.info("Successfully logged in as '{0}'",
                                 login["user"]["username"])

                expires = (login["expires"] - current_time).total_seconds()
                self.cache.set("auth", login["auth"], expires)
            except CrunchyrollAPIError as err:
                raise PluginError(u"Authentication error: {0}".format(err.msg))
        else:
            self.logger.warning(
                "No authentication provided, you won't be able to access "
                "premium restricted content"
            )

        return api

__plugin__ = Crunchyroll
