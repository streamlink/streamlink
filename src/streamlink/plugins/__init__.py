"""
    New plugins should use streamlink.plugin.Plugin instead
    of this module, but this is kept here for backwards
    compatibility.
"""

from ..exceptions import PluginError, NoStreamsError, NoPluginError
from ..plugin import Plugin
