from . import plugins
from .compat import urlparse, is_win32
from .logger import Logger
from .options import Options
from .plugins import PluginError, NoStreamsError, NoPluginError
from .stream import StreamError

import pkgutil
import imp

class Livestreamer(object):
    """
        A Livestreamer session is used to keep track of plugins,
        options and log settings.

    """

    def __init__(self):
        self.options = Options({
            "rtmpdump": is_win32 and "rtmpdump.exe" or "rtmpdump",
            "rtmpdump-proxy": None,
            "errorlog": False
        })
        self.plugins = {}
        self.logger = Logger()
        self.load_builtin_plugins()

    def set_option(self, key, value):
        """Set option *key* to *value*."""
        self.options.set(key, value)

    def get_option(self, key):
        """Return option *key*"""
        return self.options.get(key)

    def set_plugin_option(self, plugin, key, value):
        """Set plugin option *key* to *value* for the plugin *plugin*."""
        if plugin in self.plugins:
            plugin = self.plugins[plugin]
            plugin.set_option(key, value)

    def get_plugin_option(self, plugin, key):
        """Return plugin option *key* for the plugin *plugin*."""
        if plugin in self.plugins:
            plugin = self.plugins[plugin]
            return plugin.get_option(key)

    def set_loglevel(self, level):
        """
            Set the log level to *level*.
            Valid levels are: none, error, warning, info, debug.
        """
        self.logger.set_level(level)

    def set_logoutput(self, output):
        """
            Set the log output to *output*. Expects a file like
            object with a write method.
        """
        self.logger.set_output(output)

    def resolve_url(self, url):
        """
            Attempt to find the correct plugin for *url* and return it.
            Raises :exc:`NoPluginError` on failure.
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
        """
            Returns the loaded plugins for the session.
        """
        return self.plugins

    def load_builtin_plugins(self):
        self.load_plugins(plugins.__path__[0])

    def load_plugins(self, path):
        """
            Attempt to load plugins from the *path* directory.
        """
        for loader, name, ispkg in pkgutil.iter_modules([path]):
            file, pathname, desc = imp.find_module(name, [path])
            self.load_plugin(name, file, pathname, desc)

    def load_plugin(self, name, file, pathname, desc):
        module = imp.load_module(name, file, pathname, desc)

        if hasattr(module, "__plugin__"):
            plugin = getattr(module, "__plugin__")
            plugin.module = getattr(module, "__name__")
            plugin.session = self

            self.plugins[plugin.module] = plugin

        if file:
            file.close()

    @property
    def version(self):
        return __version__

__all__ = ["PluginError", "NoStreamsError", "NoPluginError", "StreamError",
           "Livestreamer"]
__version__ = "1.3.2"
