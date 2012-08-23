from . import plugins
from .compat import urlparse
from .logger import Logger
from .options import Options
from .plugins import PluginError, NoStreamsError, NoPluginError
from .stream import StreamError

import pkgutil
import imp

class Livestreamer(object):
    def __init__(self):
        self.options = Options({
            "rtmpdump": None,
            "errorlog": False
        })
        self.plugins = {}
        self.logger = Logger()
        self.load_builtin_plugins()

    def set_option(self, key, value):
        self.options.set(key, value)

    def get_option(self, key):
        return self.options.get(key)

    def set_plugin_option(self, plugin, key, value):
        if plugin in self.plugins:
            plugin = self.plugins[plugin]
            plugin.set_option(key, value)

    def get_plugin_option(self, plugin, key):
        if plugin in self.plugins:
            plugin = self.plugins[plugin]
            return plugin.get_option(key)

    def set_loglevel(self, level):
        self.logger.set_level(level)

    def set_logoutput(self, output):
        self.logger.set_output(output)

    def resolve_url(self, url):
        parsed = urlparse(url)

        if len(parsed.scheme) == 0:
            url = "http://" + url

        for name, plugin in self.plugins.items():
            if plugin.can_handle_url(url):
                obj = plugin(url)
                return obj

        raise NoPluginError

    def get_plugins(self):
        return self.plugins

    def load_builtin_plugins(self):
        for loader, name, ispkg in pkgutil.iter_modules(plugins.__path__):
            file, pathname, desc = imp.find_module(name, plugins.__path__)
            self.load_plugin(name, file, pathname, desc)

    def load_plugins(self, path):
        for loader, name, ispkg in pkgutil.iter_modules(path):
            file, pathname, desc = imp.find_module(name, path)
            self.load_plugin(name, file, pathname, desc)

    def load_plugin(self, name, file, pathname, desc):
        module = imp.load_module(name, file, pathname, desc)

        plugin = module.__plugin__
        plugin.module = module.__name__
        plugin.session = self

        self.plugins[module.__name__] = plugin

        if file:
            file.close()


__all__ = ["PluginError", "NoStreamsError", "NoPluginError", "StreamError",
           "Livestreamer"]
