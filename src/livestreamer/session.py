from . import plugins, __version__
from .compat import urlparse, is_win32
from .exceptions import NoPluginError
from .logger import Logger
from .options import Options

import pkgutil
import imp
import sys
import traceback


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
    """
    A Livestreamer session is used to keep track of plugins,
    options and log settings.

    """

    def __init__(self):
        self.options = Options({
            "rtmpdump": is_win32 and "rtmpdump.exe" or "rtmpdump",
            "rtmpdump-proxy": None,
            "ringbuffer-size": 8192*4,
            "hds-live-edge": 10.0,
            "hds-fragment-buffer": 10,
            "errorlog": False,
        })
        self.plugins = {}
        self.logger = Logger()
        self.load_builtin_plugins()

    def set_option(self, key, value):
        """
        Sets general options used by plugins and streams originating
        from this session object.

        :param key: key of the option
        :param value: value to set the option to

        """

        self.options.set(key, value)

    def get_option(self, key):
        """
        Returns current value of option

        :param key: key of the option

        """

        return self.options.get(key)

    def set_plugin_option(self, plugin, key, value):
        """
        Sets plugin specific options used by plugins originating
        from this session object.

        :param plugin: name of the plugin
        :param key: key of the option
        :param value: value to set the option to

        """

        if plugin in self.plugins:
            plugin = self.plugins[plugin]
            plugin.set_option(key, value)

    def get_plugin_option(self, plugin, key):
        """
        Returns current value of plugin specific option

        :param plugin: name of the plugin
        :param key: key of the option

        """

        if plugin in self.plugins:
            plugin = self.plugins[plugin]
            return plugin.get_option(key)

    def set_loglevel(self, level):
        """
        Sets the log level used by this session.
        Valid levels are: "none", "error", "warning", "info" and "debug".

        :param level: level of logging to output

        """

        self.logger.set_level(level)

    def set_logoutput(self, output):
        """
        Sets the log output used by this session.

        :param output: a file-like object with a write method

        """
        self.logger.set_output(output)

    def resolve_url(self, url):
        """
        Attempts to find a plugin that can use this URL.
        The default protocol (http) will be prefixed to the URL if not specified.

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

        raise NoPluginError

    def get_plugins(self):
        """Returns the loaded plugins for the session."""

        return self.plugins

    def load_builtin_plugins(self):
        self.load_plugins(plugins.__path__[0])

    def load_plugins(self, path):
        """
        Attempt to load plugins from the path specified.

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
