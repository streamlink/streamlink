from . import plugins, stream
from .compat import urlparse

def resolve_url(url):
    parsed = urlparse(url)

    if len(parsed.scheme) == 0:
        url = "http://" + url

    for name, plugin in plugins.get_plugins().items():
        if plugin.can_handle_url(url):
            obj = plugin(url)
            return obj

    raise plugins.NoPluginError()

def get_plugins():
    return plugins.get_plugins()

PluginError = plugins.PluginError
NoStreamsError = plugins.NoStreamsError
NoPluginError = plugins.NoPluginError
StreamError = stream.StreamError

plugins.load_plugins(plugins)

__all__ = ["resolve_url", "get_plugins",
           "PluginError", "NoStreamsError", "NoPluginError",
           "StreamError"]
