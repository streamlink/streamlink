# coding: utf8
"""Livestreamer extracts streams from various services.

The main compontent of Livestreamer is a command-line utility that
launches the streams in a video player.

An API is also provided that allows direct access to stream data.

Full documentation is available at http://docs.livestreamer.io/.

"""


__title__ = "livestreamer"
__version__ = "1.12.0"
__license__ = "Simplified BSD"
__author__ = "Christopher Rosell"
__copyright__ = "Copyright 2011-2015 Christopher Rosell"
__credits__ = [
    "Agustín Carrasco (@asermax)",
    "Andrew Bashore (@bashtech)",
    "Andy Mikhailenko (@neithere)",
    "Athanasios Oikonomou (@athoik)",
    "Brian Callahan (@ibara)",
    "Che (@chhe)",
    "Christopher Rosell (@chrippa)",
    "Daniel Miranda (@danielkza)",
    "Daniel Wallace (@gtmanfred)",
    "David Arvelo (@darvelo)",
    "Dominik Dabrowski (@doda)",
    "Eric J (@wormeyman)",
    "Ethan Jones (@jonesz)",
    "Gaspard Jankowiak (@gapato)",
    "Jaime Marquínez Ferrándiz (@jaimeMF)",
    "Jan Tore Morken (@jantore)",
    "John Peterson (@john-peterson)",
    "Jon Bergli Heier (@sn4kebite)",
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
    "@btiom",
    "@daslicious",
    "@MasterofJOKers",
    "@medina",
    "@monkeyphysics",
    "@nixxquality",
    "@papplampe",
    "@t0mm0",
    "@ToadKing",
    "@unintended",
    "@wolftankk",
    "@yeeeargh"
]

from .api import streams
from .exceptions import (LivestreamerError, PluginError, NoStreamsError,
                         NoPluginError, StreamError)
from .session import Livestreamer
