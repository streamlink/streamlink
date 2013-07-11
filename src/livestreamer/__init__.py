"""

Livestreamer is a CLI program that launches live streams from various
streaming services in a custom video player but also provides an API
that allows you to interact with the stream data in your own application.

"""


__title__ = "livestreamer"
__version__ = "1.4.5"
__license__ = "Simplified BSD"
__author__ = "Christopher Rosell"
__copyright__ = "Copyright 2011-2013 Christopher Rosell"
__credits__ = ["Christopher Rosell", "Athanasios Oikonomou",
               "Gaspard Jankowiak", "Dominik Dabrowski",
               "Toad King", "Niall McAndrew", "Daniel Wallace",
               "Sam Edwards", "John Peterson", "Kacper"]


from .exceptions import (PluginError, NoStreamsError,
                         NoPluginError, StreamError)
from .session import Livestreamer
