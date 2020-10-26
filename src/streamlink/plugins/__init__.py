"""
    New plugins should use streamlink.plugin.Plugin instead
    of this module, but this is kept here for backwards
    compatibility.
"""

from streamlink.exceptions import NoPluginError, NoStreamsError, PluginError
from streamlink.plugin.plugin import Plugin

__all__ = ['Plugin', 'PluginError', 'NoStreamsError', 'NoPluginError']
