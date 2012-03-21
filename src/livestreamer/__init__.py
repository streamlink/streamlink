from livestreamer import plugins
from livestreamer.compat import urlparse

import os.path

RCFILE = os.path.expanduser("~/.livestreamerrc")

def resolve_url(url):
    parsed = urlparse(url)

    if len(parsed.scheme) == 0:
        url = "http://" + url

    for name, plugin in plugins.get_plugins().items():
        if plugin.can_handle_url(url):
            obj = plugin(url)
            return (name, obj)
    return None

def get_plugins():
    return plugins.get_plugins()

plugins.load_plugins(plugins)
