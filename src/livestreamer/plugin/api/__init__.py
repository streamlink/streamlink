import sys

from types import ModuleType as module

from .http_session import HTTPSession
from .mapper import StreamMapper
from .support_plugin import load_support_plugin

__all__ = ["HTTPSession", "StreamMapper", "load_support_plugin", "http"]


class SupportPlugin(module):
    """Custom module to allow calling load_support_plugin()
       using a import statement.

    Usage::

      >>> from livestreamer.plugin.api.support_plugin import myplugin_extra

    """

    __path__ = __path__
    __file__ = __file__

    def __getattr__(self, name):
        if not name.startswith("__"):
            return load_support_plugin(name)


support_plugin_path = "livestreamer.plugin.api.support_plugin"
sys.modules[support_plugin_path] = SupportPlugin("support_plugin")
http = None
