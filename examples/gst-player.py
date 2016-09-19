#!/usr/bin/env python

from __future__ import print_function

import sys

import gi

from gi.repository import GObject as gobject, Gst as gst
from streamlink import Streamlink, StreamError, PluginError, NoPluginError


def exit(msg):
    print(msg, file=sys.stderr)
    sys.exit()


class StreamlinkPlayer(object):
    def __init__(self):
        self.fd = None
        self.mainloop = gobject.MainLoop()

        # This creates a playbin pipeline and using the appsrc source
        # we can feed it our stream data
        self.pipeline = gst.ElementFactory.make("playbin", None)
        self.pipeline.set_property("uri", "appsrc://")

        # When the playbin creates the appsrc source it will call
        # this callback and allow us to configure it
        self.pipeline.connect("source-setup", self.on_source_setup)

        # Creates a bus and set callbacks to receive errors
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect("message::eos", self.on_eos)
        self.bus.connect("message::error", self.on_error)

    def exit(self, msg):
        self.stop()
        exit(msg)

    def stop(self):
        # Stop playback and exit mainloop
        self.pipeline.set_state(gst.State.NULL)
        self.mainloop.quit()

        # Close the stream
        if self.fd:
            self.fd.close()

    def play(self, stream):
        # Attempt to open the stream
        try:
            self.fd = stream.open()
        except StreamError as err:
            self.exit("Failed to open stream: {0}".format(err))

        # Start playback
        self.pipeline.set_state(gst.State.PLAYING)
        self.mainloop.run()

    def on_source_setup(self, element, source):
        # When this callback is called the appsrc expects
        # us to feed it more data
        source.connect("need-data", self.on_source_need_data)

    def on_source_need_data(self, source, length):
        # Attempt to read data from the stream
        try:
            data = self.fd.read(length)
        except IOError as err:
            self.exit("Failed to read data from stream: {0}".format(err))

        # If data is empty it's the end of stream
        if not data:
            source.emit("end-of-stream")
            return

        # Convert the Python bytes into a GStreamer Buffer
        # and then push it to the appsrc
        buf = gst.Buffer.new_wrapped(data)
        source.emit("push-buffer", buf)

    def on_eos(self, bus, msg):
        # Stop playback on end of stream
        self.stop()

    def on_error(self, bus, msg):
        # Print error message and exit on error
        error = msg.parse_error()[1]
        self.exit(error)


def main():
    if len(sys.argv) < 3:
        exit("Usage: {0} <url> <quality>".format(sys.argv[0]))

    # Initialize and check GStreamer version
    gi.require_version("Gst", "1.0")
    gobject.threads_init()
    gst.init(None)

    # Collect arguments
    url = sys.argv[1]
    quality = sys.argv[2]

    # Create the Streamlink session
    streamlink = Streamlink()

    # Enable logging
    streamlink.set_loglevel("info")
    streamlink.set_logoutput(sys.stdout)

    # Attempt to fetch streams
    try:
        streams = streamlink.streams(url)
    except NoPluginError:
        exit("Streamlink is unable to handle the URL '{0}'".format(url))
    except PluginError as err:
        exit("Plugin error: {0}".format(err))

    if not streams:
        exit("No streams found on URL '{0}'".format(url))

    # Look for specified stream
    if quality not in streams:
        exit("Unable to find '{0}' stream on URL '{1}'".format(quality, url))

    # We found the stream
    stream = streams[quality]

    # Create the player and start playback
    player = StreamlinkPlayer()

    # Blocks until playback is done
    player.play(stream)

if __name__ == "__main__":
    main()
