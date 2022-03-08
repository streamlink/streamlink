# -*- coding: utf-8 -*-
"""Streamlink extracts streams from various services.

The main compontent of Streamlink is a command-line utility that
launches the streams in a video player.

An API is also provided that allows direct access to stream data.

Full documentation is available at https://Billy2011.github.io/streamlink-27.

"""
__version__ = "2.27.2.0-dev"
__version_date__ = "2022-03-08"
__title__ = "streamlink-27"
__license__ = "Simplified BSD"
__author__ = "Streamlink, Billy2011"
__copyright__ = "Copyright 2022 Streamlink, Billy2011"
__credits__ = ["https://github.com/streamlink/streamlink/blob/master/AUTHORS"]

from streamlink.api import streams
from streamlink.exceptions import (StreamlinkError, PluginError, NoStreamsError,
                                   NoPluginError, StreamError)
from streamlink.session import Streamlink
