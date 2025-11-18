"""Streamlink extracts streams from various services.

The main compontent of Streamlink is a command-line utility that
launches the streams in a video player.

An API is also provided that allows direct access to stream data.

Full documentation is available at https://streamlink.github.io.

Example usage as a Python module:

    >>> import streamlink
    >>>
    >>> # Quick way to get streams from a URL
    >>> streams = streamlink.streams("https://www.youtube.com/watch?v=...")
    >>>
    >>> # Or use a session for more control
    >>> session = streamlink.Streamlink()
    >>> session.set_option("http-headers", {"User-Agent": "Custom UA"})
    >>> streams = session.streams("https://twitch.tv/...")
    >>>
    >>> # Open and read a stream
    >>> stream = streams["best"]
    >>> with stream.open() as fd:
    ...     data = fd.read(1024)

"""

from streamlink._version import __version__

__title__ = "streamlink"
__license__ = "Simplified BSD"
__author__ = "Streamlink"
__copyright__ = "Copyright 2025 Streamlink"
__credits__ = ["https://github.com/streamlink/streamlink/blob/master/AUTHORS"]

# Main API
from streamlink.api import streams
from streamlink.session import Streamlink

# Exceptions
from streamlink.exceptions import (
    StreamlinkError,
    PluginError,
    FatalPluginError,
    NoStreamsError,
    NoPluginError,
    StreamError,
    StreamlinkWarning,
    StreamlinkDeprecationWarning,
)

# Stream classes
from streamlink.stream import (
    Stream,
    StreamIO,
    HTTPStream,
    HLSStream,
    MuxedHLSStream,
    DASHStream,
    MuxedStream,
    StreamIOWrapper,
    StreamIOIterWrapper,
    StreamIOThreadWrapper,
)

# Plugin base class (for custom plugins)
from streamlink.plugin import Plugin

# Options
from streamlink.options import Options

# Public API - these are the recommended imports for users
__all__ = [
    # Version
    "__version__",
    # Main API
    "streams",
    "Streamlink",
    # Exceptions
    "StreamlinkError",
    "PluginError",
    "FatalPluginError",
    "NoStreamsError",
    "NoPluginError",
    "StreamError",
    "StreamlinkWarning",
    "StreamlinkDeprecationWarning",
    # Streams
    "Stream",
    "StreamIO",
    "HTTPStream",
    "HLSStream",
    "MuxedHLSStream",
    "DASHStream",
    "MuxedStream",
    "StreamIOWrapper",
    "StreamIOIterWrapper",
    "StreamIOThreadWrapper",
    # Plugin development
    "Plugin",
    "Options",
]
