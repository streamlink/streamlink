import pkgutil
import imp

from livestreamer.logger import Logger

plugins_loaded = {}

class Plugin(object):
    def __init__(self, url):
        self.url = url
        self.args = None
        self.logger = Logger("plugin." + self.module)

    @classmethod
    def can_handle_url(self, url):
       raise NotImplementedError

    def get_streams(self):
        ranking = ["iphonelow", "iphonehigh", "240p", "320k", "360p", "850k",
                   "480p", "1400k", "720p", "2400k", "hd", "1080p", "live"]
        streams = self._get_streams()
        for rank in reversed(ranking):
            if rank in streams:
                streams["best"] = streams[rank]
                break

        return streams

    def _get_streams(self):
        raise NotImplementedError

class PluginError(Exception):
    pass

class NoStreamsError(PluginError):
    def __init__(self, url):
        PluginError.__init__(self, ("No streams found on this URL: {0}").format(url))

class NoPluginError(PluginError):
    pass

def load_plugins(plugins):
    for loader, name, ispkg in pkgutil.iter_modules(plugins.__path__):
        file, pathname, desc = imp.find_module(name, plugins.__path__)
        imp.load_module(name, file, pathname, desc)
    return plugins_loaded

def get_plugins():
    return plugins_loaded

def register_plugin(name, klass):
    plugins_loaded[name] = klass
    klass.module = name

__all__ = ["Plugin", "PluginError", "NoStreamsError", "NoPluginError",
           "load_plugins", "get_plugins", "register_plugin"]
