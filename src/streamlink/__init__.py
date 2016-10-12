# coding: utf8
"""Streamlink extracts streams from various services.

The main compontent of Streamlink is a command-line utility that
launches the streams in a video player.

An API is also provided that allows direct access to stream data.

Full documentation is available at http://docs.streamlink.io/.

"""


__title__ = "streamlink"
__version__ = "0.0.2"
__license__ = "Simplified BSD"
__author__ = "Streamlink"
__copyright__ = "Copyright 2016 Streamlink"
__credits__ = [
    "Agustín Carrasco (@asermax)",
    "Andrew Bashore (@bashtech)",
    "Andy Mikhailenko (@neithere)",
    "Athanasios Oikonomou (@athoik)",
    "Brian Callahan (@ibara)",
    "Che (@chhe)",
    "Christopher Rosell (@streamlink)",
    "Daniel Meißner (@meise)",
    "Daniel Miranda (@danielkza)",
    "Daniel Wallace (@gtmanfred)",
    "David Arvelo (@darvelo)",
    "Dominik Dabrowski (@doda)",
    "Erik G (@tboss)",
    "Eric J (@wormeyman)",
    "Ethan Jones (@jonesz)",
    "Gaspard Jankowiak (@gapato)",
    "Jaime Marquínez Ferrándiz (@jaimeMF)",
    "Jan Tore Morken (@jantore)",
    "John Peterson (@john-peterson)",
    "Jon Bergli Heier (@sn4kebite)",
    "Joseph Glanville (@josephglanville)",
    "Julian Richen (@FireDart)",
    "Kacper (@kasper93)",
    "Martin Panter (@vadmium)",
    "Max Nordlund (@maxnordlund)",
    "Michael Cheah (@cheah)",
    "Moritz Blanke",
    "Niall McAndrew (@niallm90)",
    "Niels Kräupl (@Gamewalker)",
    "Pascal Romahn (@skulblakka)",
    "Sam Edwards (@dotsam)",
    "Stefan Breunig (@breunigs)",
    "Suhail Patel (@suhailpatel)",
    "Sunaga Takahiro (@sunaga720)",
    "Vitaly Evtushenko (@eltiren)",
    "Warnar Boekkooi (@boekkooi)",
    "@blxd",
    "@btiom",
    "@daslicious",
    "@MasterofJOKers",
    "@mammothb",
    "@medina",
    "@monkeyphysics",
    "@nixxquality",
    "@papplampe",
    "@Raziel-23",
    "@t0mm0",
    "@ToadKing",
    "@unintended",
    "@wolftankk",
    "@yeeeargh"
]

from .api import streams
from .exceptions import (StreamlinkError, PluginError, NoStreamsError,
                         NoPluginError, StreamError)
from .session import Streamlink
