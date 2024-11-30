from __future__ import annotations

import warnings
from collections.abc import Callable, Iterator, Mapping
from pathlib import Path
from socket import AF_INET, AF_INET6
from typing import TYPE_CHECKING, Any, ClassVar

import urllib3.util.connection as urllib3_util_connection
from requests.adapters import HTTPAdapter

from streamlink.exceptions import StreamlinkDeprecationWarning
from streamlink.options import Options
from streamlink.session.http import TLSNoDHAdapter
from streamlink.utils.url import update_scheme


if TYPE_CHECKING:
    from streamlink.session import Streamlink


_session_file = str(Path(__file__).parent / "session.py")

_original_allowed_gai_family = urllib3_util_connection.allowed_gai_family  # type: ignore[attr-defined]


def _get_deprecation_stacklevel_offset():
    """Deal with stacklevels of both session.{g,s}et_option() and session.options.{g,s}et() calls"""
    from inspect import currentframe  # noqa: PLC0415

    frame = currentframe().f_back.f_back
    offset = 0
    while frame:
        if frame.f_code.co_filename == _session_file and frame.f_code.co_name in ("set_option", "get_option"):
            offset += 1
            break
        frame = frame.f_back

    return offset


class StreamlinkOptions(Options):
    """
    Streamlink's session options.

    The following options can be accessed using the :meth:`Streamlink.get_option() <streamlink.session.Streamlink.get_option>`
    and :meth:`Streamlink.set_option() <streamlink.session.Streamlink.set_option>` methods, as well as the regular
    :meth:`get` and :meth:`set` methods of this :class:`Options <streamlink.options.Options>` subclass.

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
        * - hls-segment-queue-threshold
          - ``float``
          - ``3``
          - Factor of the playlist's targetduration which sets the threshold for stopping early on missing segments
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
        * - ffmpeg-loglevel
          - ``str | None``
          - ``None``
          - Set FFmpeg's ``-loglevel`` value
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
        * - webbrowser
          - ``bool``
          - ``True``
          - Enable or disable support for Streamlink's webbrowser API
        * - webbrowser-executable
          - ``str | None``
          - ``None``
          - Path to the web browser's executable
        * - webbrowser-timeout
          - ``float``
          - ``20.0``
          - The maximum amount of time which the webbrowser can take to launch and execute
        * - webbrowser-cdp-host
          - ``str | None``
          - ``None``
          - Custom host for the Chrome Devtools Protocol (CDP) interface
        * - webbrowser-cdp-port
          - ``int | None``
          - ``None``
          - Custom port for the Chrome Devtools Protocol (CDP) interface
        * - webbrowser-cdp-timeout
          - ``float``
          - ``2.0``
          - The maximum amount of time for waiting on a single CDP command response
        * - webbrowser-headless
          - ``bool``
          - ``False``
          - Whether to launch the webbrowser in headless mode or not
    """

    def __init__(self, session: Streamlink) -> None:
        super().__init__({
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
            "hls-segment-queue-threshold": 3,
            "hls-segment-stream-data": False,
            "hls-segment-ignore-names": [],
            "hls-segment-key-uri": None,
            "hls-audio-select": [],
            "dash-manifest-reload-attempts": 3,
            "ffmpeg-ffmpeg": None,
            "ffmpeg-no-validation": False,
            "ffmpeg-verbose": False,
            "ffmpeg-verbose-path": None,
            "ffmpeg-loglevel": None,
            "ffmpeg-fout": None,
            "ffmpeg-video-transcode": None,
            "ffmpeg-audio-transcode": None,
            "ffmpeg-copyts": False,
            "ffmpeg-start-at-zero": False,
            "webbrowser": True,
            "webbrowser-executable": None,
            "webbrowser-timeout": 20.0,
            "webbrowser-cdp-host": None,
            "webbrowser-cdp-port": None,
            "webbrowser-cdp-timeout": 2.0,
            "webbrowser-headless": False,
        })
        self.session = session

    # ---- utils

    @staticmethod
    def _parse_key_equals_value_string(delimiter: str, value: str) -> Iterator[tuple[str, str]]:
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
        for adapter in self.session.http.adapters.values():
            if not isinstance(adapter, HTTPAdapter):
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
            urllib3_util_connection.allowed_gai_family = lambda: AF_INET  # type: ignore[attr-defined]
        else:
            self.set_explicit("ipv4", False)
            urllib3_util_connection.allowed_gai_family = lambda: AF_INET6  # type: ignore[attr-defined]

    def _set_http_proxy(self, key, value):
        self.session.http.proxies["http"] \
            = self.session.http.proxies["https"] \
            = update_scheme("https://", value, force=False)  # fmt: skip
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
    def _factory_set_http_attr_key_equals_value(delimiter: str) -> Callable[[StreamlinkOptions, str, Any], None]:
        def inner(self: "StreamlinkOptions", key: str, value: Any) -> None:
            getattr(self.session.http, self._OPTIONS_HTTP_ATTRS[key]).update(
                value if isinstance(value, dict) else dict(self._parse_key_equals_value_string(delimiter, value)),
            )

        return inner

    @staticmethod
    def _factory_set_deprecated(name: str, mapper: Callable[[Any], Any]) -> Callable[[StreamlinkOptions, str, Any], None]:
        def inner(self: StreamlinkOptions, key: str, value: Any) -> None:
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

    _OPTIONS_HTTP_ATTRS: ClassVar[Mapping[str, str]] = {
        "http-cookies": "cookies",
        "http-headers": "headers",
        "http-query-params": "params",
        "http-ssl-cert": "cert",
        "http-ssl-verify": "verify",
        "http-trust-env": "trust_env",
        "http-timeout": "timeout",
    }

    _MAP_GETTERS: ClassVar[Mapping[str, Callable[[StreamlinkOptions, str], Any]]] = {
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

    _MAP_SETTERS: ClassVar[Mapping[str, Callable[[StreamlinkOptions, str, Any], None]]] = {
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
    }
