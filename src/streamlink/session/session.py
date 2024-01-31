import logging
import pkgutil
from functools import lru_cache
from typing import Any, Dict, Optional, Tuple, Type

from streamlink import __version__, plugins
from streamlink.exceptions import NoPluginError, PluginError
from streamlink.logger import StreamlinkLogger
from streamlink.options import Options
from streamlink.plugin.api.http_session import HTTPSession
from streamlink.plugin.plugin import NO_PRIORITY, Matcher, Plugin
from streamlink.session.options import StreamlinkOptions
from streamlink.utils.l10n import Localization
from streamlink.utils.module import exec_module
from streamlink.utils.url import update_scheme


# Ensure that the Logger class returned is Streamslink's for using the API (for backwards compatibility)
logging.setLoggerClass(StreamlinkLogger)
log = logging.getLogger(".".join(__name__.split(".")[:-1]))


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

        #: Options of this session instance.
        #: :class:`StreamlinkOptions <streamlink.session.options.StreamlinkOptions>` is a subclass
        #: of :class:`Options <streamlink.options.Options>` with special getter/setter mappings.
        self.options: StreamlinkOptions = StreamlinkOptions(self)
        if options:
            self.options.update(options)
        self.plugins: Dict[str, Type[Plugin]] = {}
        self.load_builtin_plugins()

    def set_option(self, key: str, value: Any) -> None:
        """
        Sets general options used by plugins and streams originating from this session object.

        This is a convenience wrapper for :meth:`self.options.set() <streamlink.session.options.StreamlinkOptions.set>`.

        Please see :class:`StreamlinkOptions <streamlink.session.options.StreamlinkOptions>` for the available options.

        :param key: key of the option
        :param value: value to set the option to
        """

        self.options.set(key, value)

    def get_option(self, key: str) -> Any:
        """
        Returns the current value of the specified option.

        This is a convenience wrapper for :meth:`self.options.get() <streamlink.session.options.StreamlinkOptions.get>`.

        Please see :class:`StreamlinkOptions <streamlink.session.options.StreamlinkOptions>` for the available options.

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

    def streams(self, url: str, options: Optional[Options] = None, **params):
        """
        Attempts to find a plugin and extracts streams from the *url* if a plugin was found.

        :param url: a URL to match against loaded plugins
        :param options: Optional options instance passed to the resolved plugin
        :param params: Additional keyword arguments passed to :meth:`Plugin.streams() <streamlink.plugin.Plugin.streams>`
        :raises NoPluginError: on plugin resolve failure
        :return: A :class:`dict` of stream names and :class:`Stream <streamlink.stream.Stream>` instances
        """

        _pluginname, pluginclass, resolved_url = self.resolve_url(url)
        plugin = pluginclass(self, resolved_url, options)

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
        for module_info in pkgutil.iter_modules([path]):
            name = module_info.name
            # set the full plugin module name
            # use the "streamlink.plugins." prefix even for sideloaded plugins
            module_name = f"streamlink.plugins.{name}"
            try:
                mod = exec_module(module_info.module_finder, module_name)  # type: ignore[arg-type]
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
