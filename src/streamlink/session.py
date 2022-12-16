import logging
import pkgutil
import warnings
from functools import lru_cache
from socket import AF_INET, AF_INET6
from typing import Any, Callable, ClassVar, Dict, Iterator, Mapping, Optional, Tuple, Type

import urllib3.util.connection as urllib3_util_connection
from requests.adapters import HTTPAdapter

from streamlink import __version__, plugins
from streamlink.exceptions import NoPluginError, PluginError, StreamlinkDeprecationWarning
from streamlink.logger import StreamlinkLogger
from streamlink.options import Options
from streamlink.plugin.api.http_session import HTTPSession, TLSNoDHAdapter
from streamlink.plugin.plugin import NO_PRIORITY, NORMAL_PRIORITY, Matcher, Plugin
from streamlink.utils.l10n import Localization
from streamlink.utils.module import load_module
from streamlink.utils.url import update_scheme


# Ensure that the Logger class returned is Streamslink's for using the API (for backwards compatibility)
logging.setLoggerClass(StreamlinkLogger)
log = logging.getLogger(__name__)


_original_allowed_gai_family = urllib3_util_connection.allowed_gai_family  # type: ignore[attr-defined]


def _get_deprecation_stacklevel_offset():
    """Deal with stacklevels of both session.{g,s}et_option() and session.options.{g,s}et() calls"""
    from inspect import currentframe

    frame = currentframe().f_back.f_back
    offset = 0
    while frame:
        if frame.f_code.co_filename == __file__ and frame.f_code.co_name in ("set_option", "get_option"):
            offset += 1
            break
        frame = frame.f_back

    return offset


class PythonDeprecatedWarning(UserWarning):
    pass


class StreamlinkOptions(Options):
    def __init__(self, session: "Streamlink", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = session

    # ---- utils

    @staticmethod
    def _parse_key_equals_value_string(delimiter: str, value: str) -> Iterator[Tuple[str, str]]:
        for keyval in value.split(delimiter):
            try:
                key, val = keyval.split("=", 1)
                yield key.strip(), val.strip()
            except ValueError:
                continue

    @staticmethod
    def _deprecate_https_proxy(key: str) -> None:
        if key == "https-proxy":
            warnings.warn(
                "The `https-proxy` option has been deprecated in favor of a single `http-proxy` option",
                StreamlinkDeprecationWarning,
                stacklevel=4 + _get_deprecation_stacklevel_offset(),
            )

    # ---- getters

    def _get_http_proxy(self, key):
        self._deprecate_https_proxy(key)
        return self.session.http.proxies.get("https" if key == "https-proxy" else "http")

    def _get_http_attr(self, key):
        return getattr(self.session.http, self._OPTIONS_HTTP_ATTRS[key])

    # ---- setters

    def _set_interface(self, key, value):
        for scheme, adapter in self.session.http.adapters.items():
            if scheme not in ("http://", "https://"):
                continue
            if not value:
                adapter.poolmanager.connection_pool_kw.pop("source_address", None)
            else:
                # https://docs.python.org/3/library/socket.html#socket.create_connection
                adapter.poolmanager.connection_pool_kw.update(source_address=(value, 0))
        self.set_explicit(key, None if not value else value)

    def _set_ipv4_ipv6(self, key, value):
        self.set_explicit(key, value)
        if not value:
            urllib3_util_connection.allowed_gai_family = _original_allowed_gai_family  # type: ignore[attr-defined]
        elif key == "ipv4":
            self.set_explicit("ipv6", False)
            urllib3_util_connection.allowed_gai_family = (lambda: AF_INET)  # type: ignore[attr-defined]
        else:
            self.set_explicit("ipv4", False)
            urllib3_util_connection.allowed_gai_family = (lambda: AF_INET6)  # type: ignore[attr-defined]

    def _set_http_proxy(self, key, value):
        self.session.http.proxies["http"] \
            = self.session.http.proxies["https"] \
            = update_scheme("https://", value, force=False)
        self._deprecate_https_proxy(key)

    def _set_http_attr(self, key, value):
        setattr(self.session.http, self._OPTIONS_HTTP_ATTRS[key], value)

    def _set_http_disable_dh(self, key, value):
        self.set_explicit(key, value)
        if value:
            adapter = TLSNoDHAdapter()
        else:
            adapter = HTTPAdapter()

        self.session.http.mount("https://", adapter)

    @staticmethod
    def _factory_set_http_attr_key_equals_value(delimiter: str) -> Callable[["StreamlinkOptions", str, Any], None]:
        def inner(self: "StreamlinkOptions", key: str, value: Any) -> None:
            getattr(self.session.http, self._OPTIONS_HTTP_ATTRS[key]).update(
                value if isinstance(value, dict) else dict(self._parse_key_equals_value_string(delimiter, value)),
            )

        return inner

    @staticmethod
    def _factory_set_deprecated(name: str, mapper: Callable[[Any], Any]) -> Callable[["StreamlinkOptions", str, Any], None]:
        def inner(self: "StreamlinkOptions", key: str, value: Any) -> None:
            self.set_explicit(name, mapper(value))
            warnings.warn(
                f"`{key}` has been deprecated in favor of the `{name}` option",
                StreamlinkDeprecationWarning,
                stacklevel=3 + _get_deprecation_stacklevel_offset(),
            )

        return inner

    # TODO: py39 support end: remove explicit dummy context binding of static method
    _factory_set_http_attr_key_equals_value = _factory_set_http_attr_key_equals_value.__get__(object)
    _factory_set_deprecated = _factory_set_deprecated.__get__(object)

    # ----

    _OPTIONS_HTTP_ATTRS = {
        "http-cookies": "cookies",
        "http-headers": "headers",
        "http-query-params": "params",
        "http-ssl-cert": "cert",
        "http-ssl-verify": "verify",
        "http-trust-env": "trust_env",
        "http-timeout": "timeout",
    }

    _MAP_GETTERS: ClassVar[Mapping[str, Callable[["StreamlinkOptions", str], Any]]] = {
        "http-proxy": _get_http_proxy,
        "https-proxy": _get_http_proxy,
        "http-cookies": _get_http_attr,
        "http-headers": _get_http_attr,
        "http-query-params": _get_http_attr,
        "http-ssl-cert": _get_http_attr,
        "http-ssl-verify": _get_http_attr,
        "http-trust-env": _get_http_attr,
        "http-timeout": _get_http_attr,
    }

    _MAP_SETTERS: ClassVar[Mapping[str, Callable[["StreamlinkOptions", str, Any], None]]] = {
        "interface": _set_interface,
        "ipv4": _set_ipv4_ipv6,
        "ipv6": _set_ipv4_ipv6,
        "http-proxy": _set_http_proxy,
        "https-proxy": _set_http_proxy,
        "http-cookies": _factory_set_http_attr_key_equals_value(";"),
        "http-headers": _factory_set_http_attr_key_equals_value(";"),
        "http-query-params": _factory_set_http_attr_key_equals_value("&"),
        "http-disable-dh": _set_http_disable_dh,
        "http-ssl-cert": _set_http_attr,
        "http-ssl-verify": _set_http_attr,
        "http-trust-env": _set_http_attr,
        "http-timeout": _set_http_attr,
        "dash-segment-attempts": _factory_set_deprecated("stream-segment-attempts", int),
        "hls-segment-attempts": _factory_set_deprecated("stream-segment-attempts", int),
        "dash-segment-threads": _factory_set_deprecated("stream-segment-threads", int),
        "hls-segment-threads": _factory_set_deprecated("stream-segment-threads", int),
        "dash-segment-timeout": _factory_set_deprecated("stream-segment-timeout", float),
        "hls-segment-timeout": _factory_set_deprecated("stream-segment-timeout", float),
        "dash-timeout": _factory_set_deprecated("stream-timeout", float),
        "hls-timeout": _factory_set_deprecated("stream-timeout", float),
        "http-stream-timeout": _factory_set_deprecated("stream-timeout", float),
    }


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
        options: Optional[Dict[str, Any]] = None,
    ):
        """
        :param options: Custom options
        """

        self.http = HTTPSession()
        self.options = StreamlinkOptions(self, {
            "user-input-requester": None,
            "locale": None,
            "interface": None,
            "ipv4": False,
            "ipv6": False,
            "ringbuffer-size": 1024 * 1024 * 16,  # 16 MB
            "mux-subtitles": False,
            "stream-segment-attempts": 3,
            "stream-segment-threads": 1,
            "stream-segment-timeout": 10.0,
            "stream-timeout": 60.0,
            "hls-live-edge": 3,
            "hls-live-restart": False,
            "hls-start-offset": 0.0,
            "hls-duration": None,
            "hls-playlist-reload-attempts": 3,
            "hls-playlist-reload-time": "default",
            "hls-segment-stream-data": False,
            "hls-segment-ignore-names": [],
            "hls-segment-key-uri": None,
            "hls-audio-select": [],
            "dash-manifest-reload-attempts": 3,
            "ffmpeg-ffmpeg": None,
            "ffmpeg-no-validation": False,
            "ffmpeg-verbose": False,
            "ffmpeg-verbose-path": None,
            "ffmpeg-fout": None,
            "ffmpeg-video-transcode": None,
            "ffmpeg-audio-transcode": None,
            "ffmpeg-copyts": False,
            "ffmpeg-start-at-zero": False,
        })
        if options:
            self.options.update(options)
        self.plugins: Dict[str, Type[Plugin]] = {}
        self.load_builtin_plugins()

    def set_option(self, key: str, value: Any) -> None:
        """
        Sets general options used by plugins and streams originating from this session object.

        :param key: key of the option
        :param value: value to set the option to


        **Available options**:

        .. list-table::
            :header-rows: 1
            :width: 100%


            * - key
              - type
              - default
              - description
            * - user-input-requester
              - ``UserInputRequester | None``
              - ``None``
              - Instance of ``UserInputRequester`` to collect input from the user at runtime
            * - locale
              - ``str``
              - *system locale*
              - Locale setting, in the RFC 1766 format,
                e.g. ``en_US`` or ``es_ES``
            * - interface
              - ``str | None``
              - ``None``
              - Network interface address
            * - ipv4
              - ``bool``
              - ``False``
              - Resolve address names to IPv4 only, overrides ``ipv6``
            * - ipv6
              - ``bool``
              - ``False``
              - Resolve address names to IPv6 only, overrides ``ipv4``
            * - http-proxy
              - ``str | None``
              - ``None``
              - Proxy address for all HTTP/HTTPS requests
            * - https-proxy *(deprecated)*
              - ``str | None``
              - ``None``
              - Proxy address for all HTTP/HTTPS requests
            * - http-cookies
              - ``dict[str, str] | str``
              - ``{}``
              - A ``dict`` or a semicolon ``;`` delimited ``str`` of cookies to add to each HTTP/HTTPS request,
                e.g. ``foo=bar;baz=qux``
            * - http-headers
              - ``dict[str, str] | str``
              - ``{}``
              - A ``dict`` or a semicolon ``;`` delimited ``str`` of headers to add to each HTTP/HTTPS request,
                e.g. ``foo=bar;baz=qux``
            * - http-query-params
              - ``dict[str, str] | str``
              - ``{}``
              - A ``dict`` or an ampersand ``&`` delimited ``str`` of query string parameters to add to each HTTP/HTTPS request,
                e.g. ``foo=bar&baz=qux``
            * - http-trust-env
              - ``bool``
              - ``True``
              - Trust HTTP settings set in the environment,
                such as environment variables (``HTTP_PROXY``, etc.) and ``~/.netrc`` authentication
            * - http-ssl-verify
              - ``bool``
              - ``True``
              - Verify TLS/SSL certificates
            * - http-disable-dh
              - ``bool``
              - ``False``
              - Disable TLS/SSL Diffie-Hellman key exchange
            * - http-ssl-cert
              - ``str | tuple | None``
              - ``None``
              - TLS/SSL certificate to use, can be either a .pem file (``str``) or a .crt/.key pair (``tuple``)
            * - http-timeout
              - ``float``
              - ``20.0``
              - General timeout used by all HTTP/HTTPS requests, except the ones covered by other options
            * - ringbuffer-size
              - ``int``
              - ``16777216`` (16 MiB)
              - The size of the internal ring buffer used by most stream types
            * - mux-subtitles
              - ``bool``
              - ``False``
              - Make supported plugins mux available subtitles into the output stream
            * - stream-segment-attempts
              - ``int``
              - ``3``
              - Number of segment download attempts in segmented streams
            * - stream-segment-threads
              - ``int``
              - ``1``
              - The size of the thread pool used to download segments in parallel
            * - stream-segment-timeout
              - ``float``
              - ``10.0``
              - Segment connect and read timeout
            * - stream-timeout
              - ``float``
              - ``60.0``
              - Timeout for reading data from stream
            * - hls-live-edge
              - ``int``
              - ``3``
              - Number of segments from the live position of the HLS stream to start reading
            * - hls-live-restart
              - ``bool``
              - ``False``
              - Skip to the beginning of a live HLS stream, or as far back as possible
            * - hls-start-offset
              - ``float``
              - ``0.0``
              - Number of seconds to skip from the beginning of the HLS stream,
                interpreted as a negative offset for livestreams
            * - hls-duration
              - ``float | None``
              - ``None``
              - Limit the HLS stream playback duration, rounded to the nearest HLS segment
            * - hls-playlist-reload-attempts
              - ``int``
              - ``3``
              - Max number of HLS playlist reload attempts before giving up
            * - hls-playlist-reload-time
              - ``str | float``
              - ``"default"``
              - Override the HLS playlist reload time, either in seconds (``float``) or as a ``str`` keyword:

                - ``segment``: duration of the last segment
                - ``live-edge``: sum of segment durations of the ``hls-live-edge`` value minus one
                - ``default``: the playlist's target duration
            * - hls-segment-stream-data
              - ``bool``
              - ``False``
              - Stream data of HLS segment downloads to the output instead of waiting for the full response
            * - hls-segment-ignore-names
              - ``List[str]``
              - ``[]``
              - List of HLS segment names without file endings which should get filtered out
            * - hls-segment-key-uri
              - ``str | None``
              - ``None``
              - Override the address of the encrypted HLS stream's key,
                with support for the following string template variables:
                ``{url}``, ``{scheme}``, ``{netloc}``, ``{path}``, ``{query}``
            * - hls-audio-select
              - ``List[str]``
              - ``[]``
              - Select a specific audio source or sources when multiple audio sources are available,
                by language code or name, or ``"*"`` (asterisk)
            * - dash-manifest-reload-attempts
              - ``int``
              - ``3``
              - Max number of DASH manifest reload attempts before giving up
            * - hls-segment-attempts *(deprecated)*
              - ``int``
              - ``3``
              - See ``stream-segment-attempts``
            * - hls-segment-threads *(deprecated)*
              - ``int``
              - ``3``
              - See ``stream-segment-threads``
            * - hls-segment-timeout *(deprecated)*
              - ``float``
              - ``10.00``
              - See ``stream-segment-timeout``
            * - hls-timeout *(deprecated)*
              - ``float``
              - ``60.00``
              - See ``stream-timeout``
            * - dash-segment-attempts *(deprecated)*
              - ``int``
              - ``3``
              - See ``stream-segment-attempts``
            * - dash-segment-threads *(deprecated)*
              - ``int``
              - ``3``
              - See ``stream-segment-threads``
            * - dash-segment-timeout *(deprecated)*
              - ``float``
              - ``10.00``
              - See ``stream-segment-timeout``
            * - dash-timeout *(deprecated)*
              - ``float``
              - ``60.00``
              - See ``stream-timeout``
            * - http-stream-timeout *(deprecated)*
              - ``float``
              - ``60.00``
              - See ``stream-timeout``
            * - ffmpeg-ffmpeg
              - ``str | None``
              - ``None``
              - Override for the ``ffmpeg``/``ffmpeg.exe`` binary path,
                which by default gets looked up via the ``PATH`` env var
            * - ffmpeg-no-validation
              - ``bool``
              - ``False``
              - Disable FFmpeg validation and version logging
            * - ffmpeg-verbose
              - ``bool``
              - ``False``
              - Append FFmpeg's stderr stream to the Python's stderr stream
            * - ffmpeg-verbose-path
              - ``str | None``
              - ``None``
              - Write FFmpeg's stderr stream to the filesystem at the specified path
            * - ffmpeg-fout
              - ``str | None``
              - ``None``
              - Set the output format of muxed streams, e.g. ``"matroska"``
            * - ffmpeg-video-transcode
              - ``str | None``
              - ``None``
              - The codec to use if transcoding video when muxing streams, e.g. ``"h264"``
            * - ffmpeg-audio-transcode
              - ``str | None``
              - ``None``
              - The codec to use if transcoding video when muxing streams, e.g. ``"aac"``
            * - ffmpeg-copyts
              - ``bool``
              - ``False``
              - Don't shift input stream timestamps when muxing streams
            * - ffmpeg-start-at-zero
              - ``bool``
              - ``False``
              - When ``ffmpeg-copyts`` is ``True``, shift timestamps to zero
        """

        self.options.set(key, value)

    def get_option(self, key: str) -> Any:
        """
        Returns the current value of the specified option.

        :param key: key of the option
        """

        return self.options.get(key)

    @lru_cache(maxsize=128)  # noqa: B019
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
                    warnings.warn(
                        f"Resolved plugin {name} with deprecated can_handle_url API",
                        StreamlinkDeprecationWarning,
                        stacklevel=1,
                    )
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
        :param params: Additional keyword arguments passed to :meth:`Plugin.streams() <streamlink.plugin.Plugin.streams>`
        :raises NoPluginError: on plugin resolve failure
        :return: A :class:`dict` of stream names and :class:`Stream <streamlink.stream.Stream>` instances
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
        for _loader, name, _ispkg in pkgutil.iter_modules([path]):
            # set the full plugin module name
            # use the "streamlink.plugins." prefix even for sideloaded plugins
            module_name = f"streamlink.plugins.{name}"
            try:
                mod = load_module(module_name, path)
            except ImportError as err:
                log.exception(f"Failed to load plugin {name} from {path}", exc_info=err)
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
