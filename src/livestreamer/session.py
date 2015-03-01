import imp
import pkgutil
import re
import sys
import traceback

from . import plugins, __version__
from .compat import urlparse, is_win32
from .exceptions import NoPluginError, PluginError
from .logger import Logger
from .options import Options
from .plugin import api


def print_small_exception(start_after):
    type, value, traceback_ = sys.exc_info()

    tb = traceback.extract_tb(traceback_)
    index = 0

    for i, trace in enumerate(tb):
        if trace[2] == start_after:
            index = i+1
            break

    lines = traceback.format_list(tb[index:])
    lines += traceback.format_exception_only(type, value)

    for line in lines:
        sys.stderr.write(line)

    sys.stderr.write("\n")


class Livestreamer(object):
    """A Livestreamer session is used to keep track of plugins,
       options and log settings."""

    def __init__(self):
        self.http = api.HTTPSession()
        self.options = Options({
            "hds-live-edge": 10.0,
            "hds-segment-attempts": 3,
            "hds-segment-threads": 1,
            "hds-segment-timeout": 10.0,
            "hds-timeout": 60.0,
            "hls-live-edge": 3,
            "hls-segment-attempts": 3,
            "hls-segment-threads": 1,
            "hls-segment-timeout": 10.0,
            "hls-timeout": 60.0,
            "http-stream-timeout": 60.0,
            "ringbuffer-size": 1024 * 1024 * 16, # 16 MB
            "rtmp-timeout": 60.0,
            "rtmp-rtmpdump": is_win32 and "rtmpdump.exe" or "rtmpdump",
            "rtmp-proxy": None,
            "stream-segment-attempts": 3,
            "stream-segment-threads": 1,
            "stream-segment-timeout": 10.0,
            "stream-timeout": 60.0,
            "subprocess-errorlog": False
        })
        self.plugins = {}
        self.logger = Logger()
        self.load_builtin_plugins()

    def set_option(self, key, value):
        """Sets general options used by plugins and streams originating
        from this session object.

        :param key: key of the option
        :param value: value to set the option to


        **Available options**:

        ======================= =========================================
        hds-live-edge           (float) Specify the time live HDS
                                streams will start from the edge of
                                stream, default: ``10.0``

        hds-segment-attempts    (int) How many attempts should be done
                                to download each HDS segment, default: ``3``

        hds-segment-threads     (int) The size of the thread pool used
                                to download segments, default: ``1``

        hds-segment-timeout     (float) HDS segment connect and read
                                timeout, default: ``10.0``

        hds-timeout             (float) Timeout for reading data from
                                HDS streams, default: ``60.0``

        hls-live-edge           (int) How many segments from the end
                                to start live streams on, default: ``3``

        hls-segment-attempts    (int) How many attempts should be done
                                to download each HLS segment, default: ``3``

        hls-segment-threads     (int) The size of the thread pool used
                                to download segments, default: ``1``

        hls-segment-timeout     (float) HLS segment connect and read
                                timeout, default: ``10.0``

        hls-timeout             (float) Timeout for reading data from
                                HLS streams, default: ``60.0``

        http-proxy              (str) Specify a HTTP proxy to use for
                                all HTTP requests

        https-proxy             (str) Specify a HTTPS proxy to use for
                                all HTTPS requests

        http-cookies            (dict or str) A dict or a semi-colon (;)
                                delimited str of cookies to add to each
                                HTTP request, e.g. ``foo=bar;baz=qux``

        http-headers            (dict or str) A dict or semi-colon (;)
                                delimited str of headers to add to each
                                HTTP request, e.g. ``foo=bar;baz=qux``

        http-query-params       (dict or str) A dict or a ampersand (&)
                                delimited string of query parameters to
                                add to each HTTP request,
                                e.g. ``foo=bar&baz=qux``

        http-trust-env          (bool) Trust HTTP settings set in the
                                environment, such as environment
                                variables (HTTP_PROXY, etc) and
                                ~/.netrc authentication

        http-ssl-verify         (bool) Verify SSL certificates,
                                default: ``True``

        http-ssl-cert           (str or tuple) SSL certificate to use,
                                can be either a .pem file (str) or a
                                .crt/.key pair (tuple)

        http-timeout            (float) General timeout used by all HTTP
                                requests except the ones covered by
                                other options, default: ``20.0``

        http-stream-timeout     (float) Timeout for reading data from
                                HTTP streams, default: ``60.0``

        subprocess-errorlog     (bool) Log errors from subprocesses to
                                a file located in the temp directory

        ringbuffer-size         (int) The size of the internal ring
                                buffer used by most stream types,
                                default: ``16777216`` (16MB)

        rtmp-proxy              (str) Specify a proxy (SOCKS) that RTMP
                                streams will use

        rtmp-rtmpdump           (str) Specify the location of the
                                rtmpdump executable used by RTMP streams,
                                e.g. ``/usr/local/bin/rtmpdump``

        rtmp-timeout            (float) Timeout for reading data from
                                RTMP streams, default: ``60.0``

        stream-segment-attempts (int) How many attempts should be done
                                to download each segment, default: ``3``.
                                General option used by streams not
                                covered by other options.

        stream-segment-threads  (int) The size of the thread pool used
                                to download segments, default: ``1``.
                                General option used by streams not
                                covered by other options.

        stream-segment-timeout  (float) Segment connect and read
                                timeout, default: ``10.0``.
                                General option used by streams not
                                covered by other options.

        stream-timeout          (float) Timeout for reading data from
                                stream, default: ``60.0``.
                                General option used by streams not
                                covered by other options.
        ======================= =========================================

        """

        # Backwards compatibility
        if key == "rtmpdump":
            key = "rtmp-rtmpdump"
        elif key == "rtmpdump-proxy":
            key = "rtmp-proxy"
        elif key == "errorlog":
            key = "subprocess-errorlog"

        if key == "http-proxy":
            if not re.match("^http(s)?://", value):
                value = "http://" + value
            self.http.proxies["http"] = value
        elif key == "https-proxy":
            if not re.match("^http(s)?://", value):
                value = "https://" + value
            self.http.proxies["https"] = value
        elif key == "http-cookies":
            if isinstance(value, dict):
                self.http.cookies.update(value)
            else:
                self.http.parse_cookies(value)
        elif key == "http-headers":
            if isinstance(value, dict):
                self.http.headers.update(value)
            else:
                self.http.parse_headers(value)
        elif key == "http-query-params":
            if isinstance(value, dict):
                self.http.params.update(value)
            else:
                self.http.parse_query_params(value)
        elif key == "http-trust-env":
            self.http.trust_env = value
        elif key == "http-ssl-verify":
            self.http.verify = value
        elif key == "http-ssl-cert":
            self.http.cert = value
        elif key == "http-timeout":
            self.http.timeout = value
        else:
            self.options.set(key, value)

    def get_option(self, key):
        """Returns current value of specified option.

        :param key: key of the option

        """
        # Backwards compatibility
        if key == "rtmpdump":
            key = "rtmp-rtmpdump"
        elif key == "rtmpdump-proxy":
            key = "rtmp-proxy"
        elif key == "errorlog":
            key = "subprocess-errorlog"

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

    def set_plugin_option(self, plugin, key, value):
        """Sets plugin specific options used by plugins originating
        from this session object.

        :param plugin: name of the plugin
        :param key: key of the option
        :param value: value to set the option to

        """

        if plugin in self.plugins:
            plugin = self.plugins[plugin]
            plugin.set_option(key, value)

    def get_plugin_option(self, plugin, key):
        """Returns current value of plugin specific option.

        :param plugin: name of the plugin
        :param key: key of the option

        """

        if plugin in self.plugins:
            plugin = self.plugins[plugin]
            return plugin.get_option(key)

    def set_loglevel(self, level):
        """Sets the log level used by this session.

        Valid levels are: "none", "error", "warning", "info"
        and "debug".

        :param level: level of logging to output

        """

        self.logger.set_level(level)

    def set_logoutput(self, output):
        """Sets the log output used by this session.

        :param output: a file-like object with a write method

        """
        self.logger.set_output(output)

    def resolve_url(self, url):
        """Attempts to find a plugin that can use this URL.

        The default protocol (http) will be prefixed to the URL if
        not specified.

        Raises :exc:`NoPluginError` on failure.

        :param url: a URL to match against loaded plugins

        """
        parsed = urlparse(url)

        if len(parsed.scheme) == 0:
            url = "http://" + url

        for name, plugin in self.plugins.items():
            if plugin.can_handle_url(url):
                obj = plugin(url)
                return obj

        # Attempt to handle a redirect URL
        try:
            res = self.http.head(url, allow_redirects=True)
            if res.url != url:
                return self.resolve_url(res.url)
        except PluginError:
            pass

        raise NoPluginError

    def streams(self, url, **params):
        """Attempts to find a plugin and extract streams from the *url*.

        *params* are passed to :func:`Plugin.streams`.

        Raises :exc:`NoPluginError` if no plugin is found.
        """

        plugin = self.resolve_url(url)
        return plugin.streams(**params)

    def get_plugins(self):
        """Returns the loaded plugins for the session."""

        return self.plugins

    def load_builtin_plugins(self):
        self.load_plugins(plugins.__path__[0])

    def load_plugins(self, path):
        """Attempt to load plugins from the path specified.

        :param path: full path to a directory where to look for plugins

        """

        for loader, name, ispkg in pkgutil.iter_modules([path]):
            file, pathname, desc = imp.find_module(name, [path])

            try:
                self.load_plugin(name, file, pathname, desc)
            except Exception:
                sys.stderr.write("Failed to load plugin {0}:\n".format(name))
                print_small_exception("load_plugin")

                continue

    def load_plugin(self, name, file, pathname, desc):
        # Set the global http session for this plugin
        api.http = self.http
        module = imp.load_module(name, file, pathname, desc)

        if hasattr(module, "__plugin__"):
            module_name = getattr(module, "__name__")

            plugin = getattr(module, "__plugin__")
            plugin.bind(self, module_name)

            self.plugins[plugin.module] = plugin

        if file:
            file.close()

    @property
    def version(self):
        return __version__

__all__ = ["Livestreamer"]
