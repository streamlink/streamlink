import logging
import pkgutil
from functools import lru_cache
from socket import AF_INET, AF_INET6
from typing import Any, Dict, Iterator, Optional, Tuple, Type

# noinspection PyPackageRequirements
import urllib3.util.connection as urllib3_util_connection
# noinspection PyPackageRequirements
import urllib3.util.ssl_ as urllib3_util_ssl

from streamlink import __version__, plugins
from streamlink.exceptions import NoPluginError, PluginError
from streamlink.logger import StreamlinkLogger
from streamlink.options import Options
from streamlink.plugin.api.http_session import HTTPSession
from streamlink.plugin.plugin import Matcher, NORMAL_PRIORITY, NO_PRIORITY, Plugin
from streamlink.utils.l10n import Localization
from streamlink.utils.module import load_module
from streamlink.utils.url import update_scheme

# Ensure that the Logger class returned is Streamslink's for using the API (for backwards compatibility)
logging.setLoggerClass(StreamlinkLogger)
log = logging.getLogger(__name__)


# noinspection PyUnresolvedReferences
_original_allowed_gai_family = urllib3_util_connection.allowed_gai_family  # type: ignore[attr-defined]

# options which support `key1=value1;key2=value2;...` strings as value
_OPTIONS_HTTP_KEYEQUALSVALUE = {"http-cookies": "cookies", "http-headers": "headers", "http-query-params": "params"}


def _parse_keyvalue_string(value: str) -> Iterator[Tuple[str, str]]:
    for keyval in value.split(";"):
        try:
            key, val = keyval.split("=", 1)
            yield key.strip(), val.strip()
        except ValueError:
            continue


class PythonDeprecatedWarning(UserWarning):
    pass


class Streamlink:
    """
    The Streamlink session is used to load and resolve plugins, and to store options used by plugins and stream implementations.
    """

    http: HTTPSession
    """
    An instance of Streamlink's :class:`requests.Session` subclass.
    Used for any kind of HTTP request made by plugin and stream implementations.
    """

    def __init__(
        self,
        options: Optional[Dict[str, Any]] = None
    ):
        """
        :param options: Custom options
        """

        self.http = HTTPSession()
        self.options = Options({
            "interface": None,
            "ipv4": False,
            "ipv6": False,
            "hls-live-edge": 3,
            "hls-segment-ignore-names": [],
            "hls-segment-stream-data": False,
            "hls-playlist-reload-attempts": 3,
            "hls-playlist-reload-time": "default",
            "hls-start-offset": 0,
            "hls-duration": None,
            "ringbuffer-size": 1024 * 1024 * 16,  # 16 MB
            "stream-segment-attempts": 3,
            "stream-segment-threads": 1,
            "stream-segment-timeout": 10.0,
            "stream-timeout": 60.0,
            "ffmpeg-ffmpeg": None,
            "ffmpeg-no-validation": False,
            "ffmpeg-fout": None,
            "ffmpeg-video-transcode": None,
            "ffmpeg-audio-transcode": None,
            "ffmpeg-copyts": False,
            "ffmpeg-start-at-zero": False,
            "mux-subtitles": False,
            "locale": None,
            "user-input-requester": None,
        })
        if options:
            self.options.update(options)
        self.plugins: Dict[str, Type[Plugin]] = {}
        self.load_builtin_plugins()

    def set_option(self, key: str, value: Any):
        """
        Sets general options used by plugins and streams originating from this session object.

        :param key: key of the option
        :param value: value to set the option to


        **Available options**:

        ======================== =========================================
        interface                (str) Set the network interface,
                                 default: ``None``
        ipv4                     (bool) Resolve address names to IPv4 only.
                                 This option overrides ipv6, default: ``False``
        ipv6                     (bool) Resolve address names to IPv6 only.
                                 This option overrides ipv4, default: ``False``

        hls-live-edge            (int) How many segments from the end
                                 to start live streams on, default: ``3``

        hls-segment-ignore-names (str[]) List of segment names without
                                 file endings which should get filtered out,
                                 default: ``[]``

        hls-segment-stream-data  (bool) Stream HLS segment downloads,
                                 default: ``False``

        http-proxy               (str) Specify an HTTP proxy to use for
                                 all HTTP requests

        https-proxy              (str) Specify an HTTPS proxy to use for
                                 all HTTPS requests

        http-cookies             (dict or str) A dict or a semicolon ``;``
                                 delimited str of cookies to add to each
                                 HTTP request, e.g. ``foo=bar;baz=qux``

        http-headers             (dict or str) A dict or semicolon ``;``
                                 delimited str of headers to add to each
                                 HTTP request, e.g. ``foo=bar;baz=qux``

        http-query-params        (dict or str) A dict or an ampersand ``&``
                                 delimited string of query parameters to
                                 add to each HTTP request,
                                 e.g. ``foo=bar&baz=qux``

        http-trust-env           (bool) Trust HTTP settings set in the
                                 environment, such as environment
                                 variables (HTTP_PROXY, etc.) and
                                 ~/.netrc authentication

        http-ssl-verify          (bool) Verify SSL certificates,
                                 default: ``True``

        http-disable-dh          (bool) Disable SSL Diffie-Hellman key exchange

        http-ssl-cert            (str or tuple) SSL certificate to use,
                                 can be either a .pem file (str) or a
                                 .crt/.key pair (tuple)

        http-timeout             (float) General timeout used by all HTTP
                                 requests except the ones covered by
                                 other options, default: ``20.0``

        ringbuffer-size          (int) The size of the internal ring
                                 buffer used by most stream types,
                                 default: ``16777216`` (16MB)

        ffmpeg-ffmpeg            (str) Specify the location of the
                                 ffmpeg executable use by Muxing streams
                                 e.g. ``/usr/local/bin/ffmpeg``

        ffmpeg-no-validation     (bool) Disable FFmpeg validation and version logging.
                                 default: ``False``

        ffmpeg-verbose           (bool) Log stderr from ffmpeg to the
                                 console

        ffmpeg-verbose-path      (str) Specify the location of the
                                 ffmpeg stderr log file

        ffmpeg-fout              (str) The output file format
                                 when muxing with ffmpeg
                                 e.g. ``matroska``

        ffmpeg-video-transcode   (str) The codec to use if transcoding
                                 video when muxing with ffmpeg
                                 e.g. ``h264``

        ffmpeg-audio-transcode   (str) The codec to use if transcoding
                                 audio when muxing with ffmpeg
                                 e.g. ``aac``

        ffmpeg-copyts            (bool) When used with ffmpeg, do not shift input timestamps.

        ffmpeg-start-at-zero     (bool) When used with ffmpeg and copyts,
                                 shift input timestamps, so they start at zero
                                 default: ``False``

        mux-subtitles            (bool) Mux available subtitles into the
                                 output stream.

        stream-segment-attempts  (int) How many attempts should be done
                                 to download each segment, default: ``3``.

        stream-segment-threads   (int) The size of the thread pool used
                                 to download segments, default: ``1``.

        stream-segment-timeout   (float) Segment connect and read
                                 timeout, default: ``10.0``.

        stream-timeout           (float) Timeout for reading data from
                                 stream, default: ``60.0``.

        locale                   (str) Locale setting, in the RFC 1766 format
                                 e.g. en_US or es_ES
                                 default: ``system locale``.

        user-input-requester     (UserInputRequester) instance of UserInputRequester
                                 to collect input from the user at runtime.
                                 default: ``None``.
        ======================== =========================================
        """

        if key == "interface":
            for scheme, adapter in self.http.adapters.items():
                if scheme not in ("http://", "https://"):
                    continue
                if not value:
                    adapter.poolmanager.connection_pool_kw.pop("source_address")
                else:
                    adapter.poolmanager.connection_pool_kw.update(
                        # https://docs.python.org/3/library/socket.html#socket.create_connection
                        source_address=(value, 0)
                    )
            self.options.set(key, None if not value else value)

        elif key == "ipv4" or key == "ipv6":
            self.options.set(key, value)
            if not value:
                urllib3_util_connection.allowed_gai_family = _original_allowed_gai_family  # type: ignore[attr-defined]
            elif key == "ipv4":
                self.options.set("ipv6", False)
                urllib3_util_connection.allowed_gai_family = (lambda: AF_INET)  # type: ignore[attr-defined]
            else:
                self.options.set("ipv4", False)
                urllib3_util_connection.allowed_gai_family = (lambda: AF_INET6)  # type: ignore[attr-defined]

        elif key in ("http-proxy", "https-proxy"):
            self.http.proxies["http"] = update_scheme("https://", value, force=False)
            self.http.proxies["https"] = self.http.proxies["http"]
            if key == "https-proxy":
                log.warning("The https-proxy option has been deprecated in favor of a single http-proxy option")

        elif key in _OPTIONS_HTTP_KEYEQUALSVALUE:
            getattr(self.http, _OPTIONS_HTTP_KEYEQUALSVALUE[key]).update(
                value if isinstance(value, dict) else dict(_parse_keyvalue_string(value))
            )

        elif key == "http-trust-env":
            self.http.trust_env = value

        elif key == "http-ssl-verify":
            self.http.verify = value

        elif key == "http-disable-dh":
            default_ciphers = [
                item
                for item in urllib3_util_ssl.DEFAULT_CIPHERS.split(":")  # type: ignore[attr-defined]
                if item != "!DH"
            ]

            if value:
                default_ciphers.append("!DH")
            urllib3_util_ssl.DEFAULT_CIPHERS = ":".join(default_ciphers)  # type: ignore[attr-defined]

        elif key == "http-ssl-cert":
            self.http.cert = value

        elif key == "http-timeout":
            self.http.timeout = value

        # deprecated: {dash,hls}-segment-attempts
        elif key in ("dash-segment-attempts", "hls-segment-attempts"):
            self.options.set("stream-segment-attempts", int(value))
        # deprecated: {dash,hls}-segment-threads
        elif key in ("dash-segment-threads", "hls-segment-threads"):
            self.options.set("stream-segment-threads", int(value))
        # deprecated: {dash,hls}-segment-timeout
        elif key in ("dash-segment-timeout", "hls-segment-timeout"):
            self.options.set("stream-segment-timeout", float(value))
        # deprecated: {hls,dash,http-stream}-timeout
        elif key in ("dash-timeout", "hls-timeout", "http-stream-timeout"):
            self.options.set("stream-timeout", float(value))

        else:
            self.options.set(key, value)

    def get_option(self, key: str):
        """
        Returns the current value of the specified option.

        :param key: key of the option

        """

        if key == "http-proxy":
            return self.http.proxies.get("http")
        elif key == "https-proxy":
            return self.http.proxies.get("https")
        elif key == "http-cookies":
            return self.http.cookies
        elif key == "http-headers":
            return self.http.headers
        elif key == "http-query-params":
            return self.http.params
        elif key == "http-trust-env":
            return self.http.trust_env
        elif key == "http-ssl-verify":
            return self.http.verify
        elif key == "http-ssl-cert":
            return self.http.cert
        elif key == "http-timeout":
            return self.http.timeout
        else:
            return self.options.get(key)

    def set_plugin_option(self, plugin: str, key: str, value: Any) -> None:
        """
        Sets plugin specific options used by plugins originating from this session object.

        :param plugin: name of the plugin
        :param key: key of the option
        :param value: value to set the option to
        """

        if plugin in self.plugins:
            plugincls = self.plugins[plugin]
            plugincls.set_option(key, value)

    def get_plugin_option(self, plugin: str, key: str) -> Optional[Any]:
        """
        Returns the current value of the plugin specific option.

        :param plugin: name of the plugin
        :param key: key of the option
        """

        if plugin in self.plugins:
            plugincls = self.plugins[plugin]
            return plugincls.get_option(key)

    @lru_cache(maxsize=128)
    def resolve_url(
        self,
        url: str,
        follow_redirect: bool = True,
    ) -> Tuple[str, Type[Plugin], str]:
        """
        Attempts to find a plugin that can use this URL.

        The default protocol (https) will be prefixed to the URL if not specified.

        Return values of this method are cached via :meth:`functools.lru_cache`.

        :param url: a URL to match against loaded plugins
        :param follow_redirect: follow redirects
        :raises NoPluginError: on plugin resolve failure
        """

        url = update_scheme("https://", url, force=False)

        matcher: Matcher
        candidate: Optional[Tuple[str, Type[Plugin]]] = None
        priority = NO_PRIORITY
        for name, plugin in self.plugins.items():
            if plugin.matchers:
                for matcher in plugin.matchers:
                    if matcher.priority > priority and matcher.pattern.match(url) is not None:
                        candidate = name, plugin
                        priority = matcher.priority
            # TODO: remove deprecated plugin resolver
            elif hasattr(plugin, "can_handle_url") and callable(plugin.can_handle_url) and plugin.can_handle_url(url):
                prio = plugin.priority(url) if hasattr(plugin, "priority") and callable(plugin.priority) else NORMAL_PRIORITY
                if prio > priority:
                    log.warning(f"Resolved plugin {name} with deprecated can_handle_url API")
                    candidate = name, plugin
                    priority = prio

        if candidate:
            return candidate[0], candidate[1], url

        if follow_redirect:
            # Attempt to handle a redirect URL
            try:
                res = self.http.head(url, allow_redirects=True, acceptable_status=[501])  # type: ignore[call-arg]

                # Fall back to GET request if server doesn't handle HEAD.
                if res.status_code == 501:
                    res = self.http.get(url, stream=True)

                if res.url != url:
                    return self.resolve_url(res.url, follow_redirect=follow_redirect)
            except PluginError:
                pass

        raise NoPluginError

    def resolve_url_no_redirect(self, url: str) -> Tuple[str, Type[Plugin], str]:
        """
        Attempts to find a plugin that can use this URL.

        The default protocol (https) will be prefixed to the URL if not specified.

        :param url: a URL to match against loaded plugins
        :raises NoPluginError: on plugin resolve failure
        """

        return self.resolve_url(url, follow_redirect=False)

    def streams(self, url: str, **params):
        """
        Attempts to find a plugin and extracts streams from the *url* if a plugin was found.

        :param url: a URL to match against loaded plugins
        :param params: Additional keyword arguments passed to :meth:`streamlink.plugin.Plugin.streams`
        :raises NoPluginError: on plugin resolve failure
        :return: A :class:`dict` of stream names and :class:`streamlink.stream.Stream` instances
        """

        pluginname, pluginclass, resolved_url = self.resolve_url(url)
        plugin = pluginclass(self, resolved_url)

        return plugin.streams(**params)

    def get_plugins(self):
        """Returns the loaded plugins for the session."""

        return self.plugins

    def load_builtin_plugins(self):
        self.load_plugins(plugins.__path__[0])

    def load_plugins(self, path: str) -> bool:
        """
        Attempt to load plugins from the path specified.

        :param path: full path to a directory where to look for plugins
        :return: success
        """

        success = False
        for loader, name, ispkg in pkgutil.iter_modules([path]):
            # set the full plugin module name
            # use the "streamlink.plugins." prefix even for sideloaded plugins
            module_name = f"streamlink.plugins.{name}"
            try:
                mod = load_module(module_name, path)
            except ImportError:
                log.exception(f"Failed to load plugin {name} from {path}\n")
                continue

            if not hasattr(mod, "__plugin__") or not issubclass(mod.__plugin__, Plugin):
                continue
            success = True
            plugin = mod.__plugin__
            if name in self.plugins:
                log.debug(f"Plugin {name} is being overridden by {mod.__file__}")
            self.plugins[name] = plugin

        return success

    @property
    def version(self):
        return __version__

    @property
    def localization(self):
        return Localization(self.get_option("locale"))


__all__ = ["Streamlink"]
