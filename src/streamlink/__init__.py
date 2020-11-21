"""Streamlink extracts streams from various services.

The main compontent of Streamlink is a command-line utility that
launches the streams in a video player.

An API is also provided that allows direct access to stream data.

Full documentation is available at https://streamlink.github.io.

"""
from streamlink._version import get_versions

__version__ = get_versions()['version']
del get_versions
__title__ = "streamlink"
__license__ = "Simplified BSD"
__author__ = "Streamlink"
__copyright__ = "Copyright 2020 Streamlink"
__credits__ = ["https://github.com/streamlink/streamlink/blob/master/AUTHORS"]

from streamlink.api import streams
from streamlink.exceptions import (StreamlinkError, PluginError, NoStreamsError,
                                   NoPluginError, StreamError)
from streamlink.session import Streamlink
