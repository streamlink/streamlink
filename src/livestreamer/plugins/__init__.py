#!/usr/bin/env python3

import pkgutil
import imp

plugins_loaded = {}

class Plugin(object):
    def __init__(self, url):
        self.url = url
        self.args = None

    @classmethod
    def can_handle_url(self, url):
       raise NotImplementedError

    @classmethod
    def handle_parser(self, parser):
        pass

    @classmethod
    def handle_args(self, args):
        self.args = args

    def get_streams(self):
        ranking = ["iphonelow", "iphonehigh", "240p", "360p", "480p", "720p",
                   "hd", "1080p", "live"]
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
