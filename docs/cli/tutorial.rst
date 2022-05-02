Tutorial
--------

Streamlink is a command-line application, which means that the commands described
here should be typed into a terminal. On Windows, you have to open either the
`Command Prompt`_, `PowerShell`_ or `Windows Terminal`_, on macOS open the `Terminal <macOS-Terminal>`_ app,
and if you're on Linux or BSD you probably already know the drill.

The way Streamlink works is that it's only a means to extract and transport
the streams, and the playback is done by an external video player. Streamlink
works best with `VLC`_ or `mpv`_, which are also cross-platform, but other players
may be compatible too, see the :ref:`Players <players:Players>` page for a complete overview.

Now to get into actually using Streamlink, let's say you want to watch the
stream located on twitch.tv/day9tv, you start off by telling Streamlink
where to attempt to extract streams from. This is done by giving the URL to the
command :command:`streamlink` as the first argument:

.. code-block:: console

    $ streamlink twitch.tv/day9tv
    [cli][info] Found matching plugin twitch for URL twitch.tv/day9tv
    Available streams: audio, high, low, medium, mobile (worst), source (best)


.. note::
    You don't need to include the protocol when dealing with HTTP(s) URLs,
    e.g. just ``twitch.tv/day9tv`` is enough and quicker to type.


This command will tell Streamlink to attempt to extract streams from the URL
specified, and if it's successful, print out a list of available streams to choose
from.

In some cases (see :ref:`cli/protocols:Supported streaming protocols`), local files are supported
using the ``file://`` protocol, for example a local HLS playlist can be played.
Relative file paths and absolute paths are supported. All path separators are ``/``,
even on Windows.

.. code-block:: console

    $ streamlink hls://file://C:/hls/playlist.m3u8
    [cli][info] Found matching plugin stream for URL hls://file://C:/hls/playlist.m3u8
    Available streams: 180p (worst), 272p, 408p, 554p, 818p, 1744p (best)


To select a stream and start playback, simply add the stream name as a second
argument to the :command:`streamlink` command:

.. sourcecode:: console

    $ streamlink twitch.tv/day9tv 1080p60
    [cli][info] Found matching plugin twitch for URL twitch.tv/day9tv
    [cli][info] Opening stream: 1080p60 (hls)
    [cli][info] Starting player: vlc


The stream you chose should now be playing in the player. It's a common use case
to just want to start the highest quality stream and not be bothered with what it's
named. To do this, just specify ``best`` as the stream name and Streamlink will
attempt to rank the streams and open the one of highest quality. You can also
specify ``worst`` to get the lowest quality.

Now that you have a basic grasp of how Streamlink works, you may want to look
into customizing it to your own needs, such as:

- Creating a :ref:`configuration file <cli/config:Configuration file>` of options you
  want to use
- Setting up your player to :ref:`cache some data <issues:Streams are buffering/lagging>`
  before playing the stream to help avoiding buffering issues


.. _Command Prompt: https://docs.microsoft.com/en-us/windows-server/administration/windows-commands/windows-commands
.. _PowerShell: https://docs.microsoft.com/en-us/powershell/
.. _Windows Terminal: https://docs.microsoft.com/en-us/windows/terminal/get-started
.. _macOS Terminal: https://support.apple.com/guide/terminal/welcome/mac
.. _VLC: https://videolan.org/
.. _mpv: https://mpv.io/
