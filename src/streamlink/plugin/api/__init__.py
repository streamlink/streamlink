import sys
from types import ModuleType as module

from streamlink.plugin.api.http_session import HTTPSession
from streamlink.plugin.api.mapper import StreamMapper
from streamlink.plugin.api.support_plugin import load_support_plugin

__all__ = ["HTTPSession", "StreamMapper", "load_support_plugin", "http"]


class SupportPlugin(module):
    """Custom module to allow calling load_support_plugin()
       using a import statement.

    Usage::

      >>> from streamlink.plugin.api.support_plugin import myplugin_extra

    """

    __path__ = __path__
    __file__ = __file__

    def __getattr__(self, name):
        if not name.startswith("__"):
            return load_support_plugin(name)


support_plugin_path = "streamlink.plugin.api.support_plugin"
sys.modules[support_plugin_path] = SupportPlugin("support_plugin")
http = None
