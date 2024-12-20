from __future__ import annotations

import logging
import warnings
from collections.abc import Mapping
from functools import lru_cache
from typing import Any

import streamlink.compat  # noqa: F401
from streamlink import __version__
from streamlink.exceptions import NoPluginError, PluginError, StreamlinkDeprecationWarning
from streamlink.logger import StreamlinkLogger
from streamlink.options import Options
from streamlink.plugin.plugin import Plugin
from streamlink.session.http import HTTPSession
from streamlink.session.options import StreamlinkOptions
from streamlink.session.plugins import StreamlinkPlugins
from streamlink.utils.l10n import Localization
from streamlink.utils.url import update_scheme


# Ensure that the Logger class returned is Streamslink's for using the API (for backwards compatibility)
logging.setLoggerClass(StreamlinkLogger)
log = logging.getLogger(".".join(__name__.split(".")[:-1]))


class Streamlink:
    """
    The Streamlink session is used to load and resolve plugins, and to store options used by plugins and stream implementations.
    """

    def __init__(
        self,
        options: Mapping[str, Any] | Options | None = None,
        *,
        plugins_builtin: bool = True,
        plugins_lazy: bool = True,
    ):
        """
        :param options: Custom options
        :param plugins_builtin: Whether to load built-in plugins or not
        :param plugins_lazy: Load built-in plugins lazily. This option falls back to loading all built-in plugins
                             if the pre-built plugin JSON metadata is not available (e.g. in editable installs) or is invalid.
        """

        #: An instance of Streamlink's :class:`requests.Session` subclass.
        #: Used for any kind of HTTP request made by plugin and stream implementations.
        self.http: HTTPSession = HTTPSession()

        #: Options of this session instance.
        #: :class:`StreamlinkOptions <streamlink.session.options.StreamlinkOptions>` is a subclass
        #: of :class:`Options <streamlink.options.Options>` with special getter/setter mappings.
        self.options: StreamlinkOptions = StreamlinkOptions(self)
        if options:
            self.options.update(options)

        #: Plugins of this session instance.
        self.plugins: StreamlinkPlugins = StreamlinkPlugins(builtin=plugins_builtin, lazy=plugins_lazy)

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
    ) -> tuple[str, type[Plugin], str]:
        """
        Attempts to find a plugin that can use this URL.

        The default protocol (https) will be prefixed to the URL if not specified.

        Return values of this method are cached via :meth:`functools.lru_cache`.

        :param url: a URL to match against loaded plugins
        :param follow_redirect: follow redirects
        :raise NoPluginError: on plugin resolve failure
        :return: A tuple of plugin name, plugin class and resolved URL
        """

        url = update_scheme("https://", url, force=False)
        if resolved := self.plugins.match_url(url):
            return resolved[0], resolved[1], url

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

    def resolve_url_no_redirect(self, url: str) -> tuple[str, type[Plugin], str]:
        """
        Attempts to find a plugin that can use this URL.

        The default protocol (https) will be prefixed to the URL if not specified.

        :param url: a URL to match against loaded plugins
        :raise NoPluginError: on plugin resolve failure
        :return: A tuple of plugin name, plugin class and resolved URL
        """

        return self.resolve_url(url, follow_redirect=False)

    def streams(self, url: str, options: Options | None = None, **params):
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
        """
        Returns the loaded plugins of this session.

        Deprecated in favor of :meth:`plugins.get_loaded() <streamlink.session.plugins.StreamlinkPlugins.get_loaded>`.
        """
        warnings.warn(
            "`Streamlink.get_plugins()` has been deprecated in favor of `Streamlink.plugins.get_loaded()`",
            StreamlinkDeprecationWarning,
            stacklevel=2,
        )
        return self.plugins.get_loaded()

    def load_builtin_plugins(self):
        """
        Loads Streamlink's built-in plugins.

        Deprecated in favor of using the :class:`plugins_builtin <streamlink.session.Streamlink>` keyword argument.
        """
        warnings.warn(
            "`Streamlink.load_builtin_plugins()` has been deprecated in favor of the `plugins_builtin` keyword argument",
            StreamlinkDeprecationWarning,
            stacklevel=2,
        )
        self.plugins.load_builtin()

    def load_plugins(self, path: str) -> bool:
        """
        Loads plugins from a specific path.

        Deprecated in favor of :meth:`plugins.load_path() <streamlink.session.plugins.StreamlinkPlugins.load_path>`.
        """
        warnings.warn(
            "`Streamlink.load_plugins()` has been deprecated in favor of `Streamlink.plugins.load_path()`",
            StreamlinkDeprecationWarning,
            stacklevel=2,
        )
        return self.plugins.load_path(path)

    @property
    def version(self):
        return __version__

    @property
    def localization(self):
        return Localization(self.get_option("locale"))


__all__ = ["Streamlink"]
