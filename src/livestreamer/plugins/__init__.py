#!/usr/bin/env python3

import pkgutil
import imp

plugins_loaded = {}

class Plugin(object):
    def can_handle_url(self, url):
        raise NotImplementedError

    def get_streams(self, channel):
        raise NotImplementedError

    def stream_cmdline(self, stream, filename):
        raise NotImplementedError

    def handle_parser(self, parser):
        pass

    def handle_args(self, args):
        self.args = args


def load_plugins(plugins):
    for loader, name, ispkg in pkgutil.iter_modules(plugins.__path__):
        file, pathname, desc = imp.find_module(name, plugins.__path__)
        imp.load_module(name, file, pathname, desc)
    return plugins_loaded


def get_plugins():
    return plugins_loaded

def register_plugin(name, klass):
    obj = klass()
    plugins_loaded[name] = obj
