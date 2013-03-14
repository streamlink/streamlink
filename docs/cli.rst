.. _cli:

Command Line Interface
======================

The CLI can be used to either pipe streams to a video player for playback or download them to a file.

Tutorial
--------

The CLI is designed to be as simple as possible to use, in two or less steps you can start playback
of your favorite stream in a desktop video player such as `VLC <http://videolan.org/>`_ or `MPlayer <http://www.mplayerhq.hu/>`_.

Let's say you want to watch the stream located on http://twitch.tv/day9tv, you start off by telling Livestreamer
where to to find information about your stream by giving the URL to ``livestreamer`` as the first argument.
You do not need to specify the whole URL including ``http://``, just ``twitch.tv/day9tv`` will do just fine.

.. code-block:: console

    $ livestreamer twitch.tv/day9tv
    [cli][info] Found matching plugin justintv for URL twitch.tv/day9tv
    Found streams: 240p, 360p, 480p, 720p (best), iphonehigh, iphonelow (worst)

Livestreamer will find out what streams are available and print them out for you to choose from. Simply give ``livestreamer``
the stream as the second argument and playback will start in your video player of choice.

The words printed next to stream names within a parantheses are synonyms and can be used when selecting stream to play.
In this case the ``best`` stream is a reference to the stream that is considered to be of highest quality, e.g ``720p``.

.. sourcecode:: console

    $ livestreamer twitch.tv/day9tv best
    [cli][info] Found matching plugin justintv for URL twitch.tv/day9tv
    [cli][info] Opening stream: 720p
    [cli][info] Starting player: vlc

The default player is `VLC <http://videolan.org/>`_, but it can be easily changed using the ``--player`` argument.
It is recommended to create a `Configuration file`_ for arguments you wish to be used everytime.

Full list of command line arguments
-----------------------------------

.. program:: livestreamer

.. cmdoption:: -h, --help

    Show help message and exit

.. cmdoption:: -V, --version

    Show program's version number and exit

.. cmdoption:: -u, --plugins

    Print all currently installed plugins

.. cmdoption:: -l level, --loglevel level

    Set log level, valid levels: none, error, warning, info, debug

.. cmdoption:: -j, --json

    Output JSON instead of the normal text output and
    disable log output, useful for external scripting


*Player options*

.. cmdoption:: -p player, --player player

    Command-line for player, default is **vlc**

.. cmdoption:: -q, --quiet-player

    Hide all player console output

.. cmdoption:: -n, --fifo

    Play file using a named pipe instead of stdin (can
    help with incompatible media players)

*File output options*

.. cmdoption::  -o filename, --output filename

    Write stream to file instead of playing it

.. cmdoption:: -f, --force

    Always write to file even if it already exists

.. cmdoption:: -O, --stdout

    Write stream to stdout instead of playing it

*Stream options*

.. cmdoption:: -c, --cmdline

    Print command-line used internally to play stream,
    this may not be available on all streams

.. cmdoption:: -e, --errorlog

    Log possible errors from internal command-line to a
    temporary file, use when debugging

.. cmdoption:: -r path, --rtmpdump path

    Specify location of rtmpdump executable, e.g.
    /usr/local/bin/rtmpdump

.. cmdoption:: --rtmpdump-proxy host:port

    Specify a proxy (SOCKS) that rtmpdump will use

.. cmdoption:: --hds-live-edge seconds

    Specify the time live HDS streams will start from the
    edge of stream, default is **10.0**

.. cmdoption::  --hds-fragment-buffer fragments

    Specify the maximum amount of fragments to buffer,
    this controls the maximum size of the ringbuffer,
    default is **10**

.. cmdoption:: --ringbuffer-size size

    Specify a maximum size (bytes) for the ringbuffer used
    by some stream types, default is **32768**


*Plugin options*

.. cmdoption:: --plugin-dirs directory

    Attempts to load plugins from these directories.
    Multiple directories can be used by separating them
    with a semicolon (;)

.. cmdoption:: --stream-priority priorities

    When there are multiple streams with the same name but
    different streaming types, these priorities will be
    used. Should be specified as a comma-delimited list,
    default is **rtmp,hls,hds,http,akamaihd**

.. cmdoption:: --jtv-cookie cookie

    Specify JustinTV cookie to allow access to
    subscription channels, e.g '_twitch_session_id=xxxxxx; persistent=xxxxx;'

.. cmdoption:: --gomtv-cookie cookie

    Specify GOMTV cookie to allow access to streams,
    e.g. 'SES_USERNO=xxx; SES_STATE=xxx; SES_MEMBERNICK=xxx; SES_USERNICK=xxx;'

.. cmdoption:: --gomtv-username username

    Specify GOMTV username to allow access to streams

.. cmdoption:: --gomtv-password [password]

    Specify GOMTV password to allow access to streams (If
    left blank you will be prompted)


Configuration file
------------------

Writing the command line arguments everytime is painful, that's why Livestreamer
is capable of reading arguments from a file instead, a sort of configuration file.
Livestreamer will look for this file in different locations depending on platform:

**Unix-like OSs**
  ``~/.livestreamerrc``

**Windows**
  ``%APPDATA%\livestreamer\livestreamerrc``


The file should contain one argument per line, like this:

.. code-block:: console

    player=mplayer -cache 2048
    gomtv-username=username
    gomtv-password=password


Common issues
-------------

**Livestreamer exits with error "Unable to read from stream" or "Error while executing subprocess" on Twitch/Justin.tv streams**

When building rtmpdump from source it may link with a already existing (probably older) librtmp version instead of using it's
own version. On Debian/Ubuntu it is recommended to use the official packages of *librtmp0* and *rtmpdump* version
*2.4+20111222.git4e06e21* or newer. This version contains the necessary code to play Twitch/Justin.tv streams and
avoids any conflicts. It should be available in the testing or unstable repositories if it's not available in stable yet.

**VLC fails to play with a error message**

VLC version *2.0.1* and *2.0.2* contains a bug that prevents it from reading data from standard input.
This has been fixed in version *2.0.3*.

**Streams are buffering/lagging**

By default most players do not cache the input from stdin, here is a few command arguments you can pass to some common players:

- ``mplayer --cache <kbytes>`` (between 1024 and 8192 is recommended)
- ``vlc --file-caching <milliseconds>`` (between 1000 and 10000 is recommended)

These options can be used by passing ``--player`` to livestreamer.


Advanced usage
--------------

Playing built-in streaming protocols directly
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

There are many types of streaming protocols used by services today and Livestreamer
implements most of them. It is possible to tell livestreamer to access a streaming
protocol directly instead of relying on a plugin to find the information for you.

A protocol can be accessed directly by specifying it in the URL format: `protocol://path key=value`.

For example, to access a RTMP stream which requires parameters to be passed along to the stream:

.. code-block:: console

    $ livestreamer "rtmp://streaming.server.net/playpath live=1 swfVfy=http://server.net/flashplayer.swf"


Most streaming technologies simply requires you to pass a HTTP URL, this is an Adobe HDS stream:

.. code-block:: console

    $ livestreamer hds://http://streaming.server.net/playpath/manifest.f4m


Livestreamer currently supports these protocols:


+-------------------------------+-----------------------------------------------+
| Name                          | Prefix                                        |
+===============================+===============================================+
| Adobe HTTP Dynamic Streaming  | hds://                                        |
+-------------------------------+-----------------------------------------------+
| Akamai HD Adaptive Streaming  | akamaihd://                                   |
+-------------------------------+-----------------------------------------------+
| Apple HTTP Live Streaming     | hls:// hlvsvariant://                         |
+-------------------------------+-----------------------------------------------+
| Real Time Messaging Protocol  | rtmp:// rmpte:// rmpts:// rtmpt:// rtmpte://  |
+-------------------------------+-----------------------------------------------+

