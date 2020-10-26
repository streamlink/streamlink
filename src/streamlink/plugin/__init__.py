from streamlink.exceptions import PluginError
from streamlink.options import Argument as PluginArgument, Arguments as PluginArguments, Options as PluginOptions
from streamlink.plugin.plugin import Plugin

__all__ = ["Plugin", "PluginError", "PluginOptions", "PluginArguments", "PluginArgument"]
