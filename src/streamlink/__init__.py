# -*- coding: utf-8 -*-
"""Streamlink extracts streams from various services.

The main compontent of Streamlink is a command-line utility that
launches the streams in a video player.

An API is also provided that allows direct access to stream data.

Full documentation is available at https://streamlink.github.io.

"""
__version__ = "1.27.0.0"
__version_date__ = "2020-10-18"
__title__ = "streamlink"
__license__ = "Simplified BSD"
__author__ = "Streamlink"
__copyright__ = "Copyright 2020 Streamlink"
__credits__ = ["https://github.com/streamlink/streamlink/blob/master/AUTHORS"]

from .api import streams
from .exceptions import (StreamlinkError, PluginError, NoStreamsError,
                         NoPluginError, StreamError)
from .session import Streamlink
