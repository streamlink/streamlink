#!/usr/bin/env python3

import pkgutil
import imp

plugins_loaded = {}

class Plugin(object):
    def __init__(self, url):
        self.url = url

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
        raise NotImplementedError

def load_plugins(plugins):
    for loader, name, ispkg in pkgutil.iter_modules(plugins.__path__):
        file, pathname, desc = imp.find_module(name, plugins.__path__)
        imp.load_module(name, file, pathname, desc)
    return plugins_loaded


def get_plugins():
    return plugins_loaded

def register_plugin(name, klass):
    plugins_loaded[name] = klass
