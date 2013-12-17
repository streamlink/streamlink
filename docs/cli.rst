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
    Found streams: 240p, 360p, 480p, 720p (best), mobile_high, mobile_low (worst)

Livestreamer will find out what streams are available and print them out for you to choose from. Simply give ``livestreamer``
the stream as the second argument and playback will start in your video player of choice.

The words printed next to stream names within a parantheses are synonyms and can be used when selecting stream to play.
In this case the ``best`` stream is a reference to the stream that is considered to be of highest quality, e.g ``720p``.

.. sourcecode:: console

    $ livestreamer twitch.tv/day9tv best
    [cli][info] Found matching plugin justintv for URL twitch.tv/day9tv
    [cli][info] Opening stream: 720p
    [cli][info] Starting player: vlc

The default player is `VLC <http://videolan.org/>`_, but it can be easily changed using the ``--player`` option.


Now that you have a basic grasp of how Livestreamer works, you may want to look into
customizing it to your own needs, such as:

- Creating a :ref:`configuration file <cli-livestreamerrc>` of options you want to use
- Setting up your player to :ref:`cache some data <issues-player_caching>`
  before playing the stream to help avoiding lag issues


.. _cli-livestreamerrc:

Configuration file
------------------

Writing the command line options every time is painful, that's why Livestreamer
is capable of reading options from a file instead, a sort of configuration file.
Livestreamer will look for this file in different locations depending on your platform:

**Unix-like OSs**
  - ``~/.config/livestreamer/config``
  - ``~/.livestreamerrc``

**Windows**
  - ``%APPDATA%\livestreamer\livestreamerrc``


The file should contain one option per line in the format ``option[=value]``, like this:

.. code-block:: bash

    player=mplayer -cache 2048
    player-no-close
    jtv-cookie=_twitch_session_id=xxxxxx; persistent=xxxxx;
    gomtv-cookie=SES_MEMBERNO=xxx; SES_STATE=xxx; SES_MEMBERNICK=xxx; SES_USERNICK=xxx;


For a list of all the supported options see :ref:`cli-options`.

Plugin specific usage
---------------------


Authenticating with Twitch
^^^^^^^^^^^^^^^^^^^^^^^^^^

It's possible to access subscription content on Twitch by giving Livestreamer
access to your account. There are two methods to authenticate Livestreamer
to Twitch: Application authorization via OAuth or re-using your web browsers
cookies.

Using the OAuth method is recommended since it is easier and will never expire
(unless access is revoked in your Twitch settings or a new access token is
created), unlike cookies which may stop working if you log out in your browser.


**Application authorization via OAuth**

To authenticate Livestreamer with your Twitch account, simply run this command:

.. sourcecode:: console

    $ livestreamer --twitch-oauth-authenticate


This will open a web browser where Twitch will ask you if you want to give
Livestreamer permission to access your account, then forward you to a page
with further instructions.


**Cookies**

Cookies should be specified in a key value list separated by a semicolon.
In this case only the `_twitch_session_id` and `persistent` keys are required
by Twitch. For example:


.. sourcecode:: console

    $ livestreamer --twitch-cookie "_twitch_session_id=xxxxxx; persistent=xxxxx" twitch.tv/ignproleague
    [plugin.justintv][info] Attempting to authenticate using cookies
    [plugin.justintv][info] Successfully logged in as <username>


Extracting cookies from your web browser varies from browser to browser, try
googling "<browser name> view cookies".

It's recommended to save these cookies in your
:ref:`configuration file <cli-livestreamerrc>` rather than specifying them
manually every time.

.. note::

    Authenticating with Justin.tv is not possible since their video system
    overhaul, but may be a unintended bug and could be fixed in the future.


Authenticating with GOMTV.net
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

GOMTV.net requires authenticating with an account before allowing you to access any of their content.
This is done easiest by following these steps:

.. sourcecode:: console

    $ livestreamer --gomtv-username user@email.com gomtv.net

This will cause Livestreamer to prompt you for your password and then attempt to login, giving you an output similar to this when successful:

.. sourcecode:: console

    $ livestreamer --gomtv-username user@email.com gomtv.net
    Enter GOMTV password:
    [plugin.gomtv][info] Attempting to authenticate with username and password
    [plugin.gomtv][info] Successfully logged in as <username>
    [plugin.gomtv][info] Cookie for reusing this session: SES_MEMBERNO=xxxxxxxxxx; SES_STATE=xxxxxxxxxxx; SES_MEMBERNICK=xxxxxx; SES_USERNICK=username;


The important part of this output is the last line, that's the cookies used to access this login session. To use these cookies pass them to the ``--gomtv-cookie`` option. It's recommended to save these cookies in your :ref:`configuration file <cli-livestreamerrc>` rather than specifying them manually every time.

These instructions are for authenticating with a regular user account, if you are using a Facebook or Twitter account to authenticate you'll need to extract your cookies from your web browser instead. Extracting cookies from your web browser varies from browser to browser, try googling "<browser name> view cookies".


Advanced usage
--------------

Sideloading plugins
^^^^^^^^^^^^^^^^^^^

Livestreamer will attempt to load plugins from these directories:

**Unix-like OSs**
  - ``~/.config/livestreamer/plugins``

**Windows**
  - ``%APPDATA%\livestreamer\plugins``


.. note::

    If a plugin is added with the same name as a built-in plugin then
    the added plugin will take precedence. This is useful if you want
    to upgrade plugins independently of the Livestreamer version.


Playing built-in streaming protocols directly
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

There are many types of streaming protocols used by services today and Livestreamer
implements most of them. It is possible to tell Livestreamer to access a streaming
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
| Real Time Messaging Protocol  | rtmp:// rtmpe:// rtmps:// rtmpt:// rtmpte://  |
+-------------------------------+-----------------------------------------------+


.. _cli-options:

Command line options
--------------------

.. program:: livestreamer

.. cmdoption:: -h, --help

    Show help message and exit

.. cmdoption:: -V, --version

    Show program's version number and exit

.. cmdoption:: --plugins

    Print all currently installed plugins

.. cmdoption:: -l level, --loglevel level

    Set log level, valid levels: ``none``, ``error``, ``warning``, ``info``, ``debug``

.. cmdoption:: -Q, --quiet

    Alias for ``--loglevel none``

.. cmdoption:: -j, --json

    Output JSON instead of the normal text output and
    disable log output, useful for external scripting

.. cmdoption:: --http-proxy http://hostname:port/

    Specify a HTTP proxy. This is the same as setting
    the environment variable ``http_proxy``.

    .. versionadded:: 1.7.0

.. cmdoption:: --https-proxy https://hostname:port/

    Specify a HTTPS proxy. This is the same as setting
    the environment variable ``https_proxy``.

    .. versionadded:: 1.7.0


Player options
^^^^^^^^^^^^^^

.. cmdoption:: -p player, --player player

    Player command-line to start, by default VLC will be
    used if it is installed

.. cmdoption:: -a, --player-args

    The arguments passed to the player. These formatting
    variables are available: filename. Default is ``'{filename}'``

    .. versionadded:: 1.6.0

.. cmdoption:: -v, --verbose-player

    Show all player console output

.. cmdoption:: -n, --player-fifo, --fifo

    Make the player read the stream through a named pipe
    (useful if your player can't read from stdin)

.. cmdoption:: --player-http

    Make the player read the stream using HTTP
    (useful if your player can't read from stdin)

    .. versionadded:: 1.6.0

.. cmdoption:: --player-continuous-http

    Make the player read the stream using HTTP, but unlike
    ``--player-http`` will continuously try to open the stream
    if the player requests it. This makes it possible to
    handle stream disconnects if your player is capable of
    reconnecting to a HTTP stream, e.g ``'vlc --repeat'``

    .. versionadded:: 1.6.0

.. cmdoption:: --player-passthrough types

    A comma-delimited list of stream types to pass to the
    player as a filename rather than piping the data. Make
    sure your player can handle the stream type when using this.
    Supported stream types are: ``hls``, ``http``, ``rtmp``

    .. versionadded:: 1.6.0

.. cmdoption:: --player-no-close

    By default Livestreamer will close the player when the
    stream ends. This option will let the player decide
    when to exit.

    .. versionadded:: 1.7.0

File output options
^^^^^^^^^^^^^^^^^^^

.. cmdoption::  -o filename, --output filename

    Write stream to file instead of playing it

.. cmdoption:: -f, --force

    Always write to file even if it already exists

.. cmdoption:: -O, --stdout

    Write stream to stdout instead of playing it


Stream options
^^^^^^^^^^^^^^

.. cmdoption:: -c, --cmdline

    Print command-line used internally to play stream,
    this may not be available on all streams

.. cmdoption:: -e, --errorlog

    Log possible errors from internal command-line to a
    temporary file, use when debugging

.. cmdoption:: -r path, --rtmpdump path

    Specify location of rtmpdump executable, e.g.
    ``/usr/local/bin/rtmpdump``

.. cmdoption:: --rtmpdump-proxy host:port

    Specify a proxy (SOCKS) that rtmpdump will use

.. cmdoption:: --hds-live-edge seconds

    Specify the time live HDS streams will start from the
    edge of stream, default is ``10.0``

.. cmdoption::  --hds-fragment-buffer fragments

    Specify the maximum amount of fragments to buffer,
    this controls the maximum size of the ringbuffer,
    default is ``10``

.. cmdoption:: --ringbuffer-size size

    Specify a maximum size (bytes) for the ringbuffer used
    by some stream types, default is ``32768``. Used by RTMP
    and HLS. Use ``--hds-fragment-buffer`` for HDS.


Plugin options
^^^^^^^^^^^^^^

.. cmdoption:: --plugin-dirs directory

    Attempts to load plugins from these directories.
    Multiple directories can be used by separating them
    with a semicolon (;)


.. cmdoption:: --stream-types types, --stream-priority types

    A comma-delimited list of stream types to allow. The
    order will be used to separate streams when there are
    multiple streams with the same name and different
    stream types. Default is ``rtmp,hls,hds,http,akamaihd``


.. cmdoption:: --stream-sorting-excludes streams

    Fine tune best/worst synonyms by excluding unwanted
    streams. Uses a filter expression in the format
    ``[operator]<value>``. For example the filter ``>480p`` will
    exclude streams ranked higher than '480p'. Valid
    operators are ``>``, ``>=``, ``<`` and ``<=``. If no operator is
    specified then equality is tested.

    Multiple filters can be used by separating each
    expression with a comma. For example ``>480p,>mobile_medium``
    will exclude streams from two quality types.

.. cmdoption:: --jtv-cookie cookie, --twitch-cookie cookie

    Specify Twitch/Justin.tv cookies to allow access to
    subscription channels, e.g ``'_twitch_session_id=xxxxxx; persistent=xxxxx;'``

.. cmdoption:: --jtv-password password, --twitch-password password

   Use this to access password protected streams.

   .. versionadded:: 1.6.0

.. cmdoption:: --twitch-oauth-token token

   Specify a OAuth token to allow Livestreamer to access Twitch using
   your account.

   .. versionadded:: 1.7.2

.. cmdoption:: --twitch-oauth-authenticate

   Opens a web browser where you can grant Livestreamer access to your
   Twitch account.

   .. versionadded:: 1.7.2

.. cmdoption:: --gomtv-cookie cookie

    Specify GOMTV cookie to allow access to streams,
    e.g. ``'SES_MEMBERNO=xxx; SES_STATE=xxx; SES_MEMBERNICK=xxx; SES_USERNICK=xxx;'``

.. cmdoption:: --gomtv-username username

    Specify GOMTV username to allow access to streams

.. cmdoption:: --gomtv-password [password]

    Specify GOMTV password to allow access to streams (If
    left blank you will be prompted)



