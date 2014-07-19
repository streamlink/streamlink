.. _cli:

Command-Line Interface
======================

The CLI can be used to either pipe streams to a video player for playback or
download them directly to a file.

Tutorial
--------

The CLI is designed to be as simple as possible to use, in two or less steps
you can start playback of your favorite stream in a desktop video player such
as `VLC <http://videolan.org/>`_ or `mpv <http://mpv.io/>`_.

Let's say you want to watch the stream located on http://twitch.tv/day9tv, you
start off by telling Livestreamer where to to find information about your stream
by giving the URL to the command :command:`livestreamer` as the first argument.

You do not need to include the protocol when dealing with HTTP URLs,
just ``twitch.tv/day9tv`` will do.

.. code-block:: console

    $ livestreamer twitch.tv/day9tv
    [cli][info] Found matching plugin twitch for URL twitch.tv/day9tv
    Available streams: audio, high, low, medium, mobile (worst), source (best)

Livestreamer will find out what streams are available and print them out for you
to choose from. Simply give :command:`livestreamer` the stream as the second
argument and playback will start in your video player of choice.

The words printed next to stream names within a parantheses are synonyms and
can be used when selecting stream to play. In this case the ``best`` stream is
a reference to the stream that is considered to be of highest quality,
e.g. ``source``.

.. sourcecode:: console

    $ livestreamer twitch.tv/day9tv best
    [cli][info] Found matching plugin twitch for URL twitch.tv/day9tv
    [cli][info] Opening stream: source
    [cli][info] Starting player: vlc

The default player is `VLC <http://videolan.org/>`_, but it can be easily changed
using the :option:`--player` option.


Now that you have a basic grasp of how Livestreamer works, you may want to look
into customizing it to your own needs, such as:

- Creating a :ref:`configuration file <cli-livestreamerrc>` of options you
  want to use
- Setting up your player to :ref:`cache some data <issues-player_caching>`
  before playing the stream to help avoiding lag issues


.. _cli-livestreamerrc:

Configuration file
------------------

Writing the command-line options every time is painful, that's why Livestreamer
is capable of reading options from a configuration file instead.
Livestreamer will look for config files in different locations depending on
your platform:

================= ====================================================
Platform          Location
================= ====================================================
Unix-like (POSIX) - $XDG_CONFIG_HOME/livestreamer/config
                  - ~/.livestreamerrc
Windows           %APPDATA%\\livestreamer\\livestreamerrc
================= ====================================================

.. note::

  - `$XDG_CONFIG_HOME` is ``~/.config`` if it has not been overridden
  - `%APPDATA%` is usually ``<your user directory>\Application Data``


You can also specify the location yourself using the :option:`--config` option.

Syntax
^^^^^^

The file should contain one :ref:`command-line option <cli-options>`
(omitting the dashes) per line in this format::

  option[=value]

.. note::

  Any quotes used will be part of the value, so only use when necessary.

Example
^^^^^^^

.. code-block:: bash

    # Player options
    player=mpv --cache 2048
    player-no-close

    # Authenticate with Twitch
    twitch-oauth-token=mytoken


Plugin specific configuration file
----------------------------------

You may want to use specific options for some plugins only. This
can be accomplished by placing those settings inside a plugin specific
config file. Options inside these config files will override the main
config file when a URL matching the plugin is used.

Livestreamer expects this config to be named like the main config but
with ``.<plugin name>`` attached to the end.

Examples
^^^^^^^^

================= ====================================================
Platform          Location
================= ====================================================
Unix-like (POSIX) - $XDG_CONFIG_HOME/livestreamer/config\ ``.twitch``
                  - ~/.livestreamerrc\ ``.ustreamtv``
Windows           %APPDATA%\\livestreamer\\livestreamerrc\ ``.youtube``
================= ====================================================

Have a look at the :ref:`list of plugins <plugin_matrix>` to see
the name of each built-in plugin.


Plugin specific usage
---------------------

Authenticating with Twitch
^^^^^^^^^^^^^^^^^^^^^^^^^^

It's possible to access subscription content on Twitch by giving Livestreamer
access to your account.

Authentication is done by creating an OAuth token that Livestreamer will
use to access your account. It's done like this:

.. sourcecode:: console

    $ livestreamer --twitch-oauth-authenticate


This will open a web browser where Twitch will ask you if you want to give
Livestreamer permission to access your account, then forwards you to a page
with further instructions on how to use it.


Authenticating with Crunchyroll
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Crunchyroll requires authenticating with a premium account to access some of
their content. To do so, the plugin provides a couple of options to input your
information, :option:`--crunchyroll-username` and :option:`--crunchyroll-password`.

You can login like this:

.. sourcecode:: console

    $ livestreamer --crunchyroll-username=xxxx --crunchyroll-password=xxx http://crunchyroll.com/a-crunchyroll-episode-link

.. note::

    If you omit the password, livestreamer will ask for it.

Once logged in, the plugin makes sure to save the session credentials to avoid
asking your username and password again.

Neverthless, these credentials are valid for a limited amount of time, so it
might be a good idea to save your username and password in your
:ref:`configuration file <cli-livestreamerrc>` anyway.

.. warning::

    The API this plugin uses isn't supposed to be available to use it on
    computers. The plugin tries to blend in as a valid device using custom
    headers and following the API usual flow (e.g. reusing credentials), but
    this does not assure that your account will be safe from being spotted for
    unusual behavior.

HTTP proxy with Crunchyroll
^^^^^^^^^^^^^^^^^^^^^^^^^^^
You can use the :option:`--http-proxy` **and** :option:`--https-proxy`
options (you need both since the plugin uses both protocols) to access the
Crunchyroll servers through a proxy to be able to stream region locked content.

When doing this, it's very probable that you will get denied to access the
stream; this occurs because the session and credentials used by the plugin
where obtained when logged from your own region, and the server still assumes
you're in that region.

For this, the plugin provides the :option:`--crunchyroll-purge-credentials`
option, which removes your saved session and credentials and tries to log
in again using your username and password.

Sideloading plugins
-------------------

Livestreamer will attempt to load standalone plugins from these directories:

================= ====================================================
Platform          Location
================= ====================================================
Unix-like (POSIX) $XDG_CONFIG_HOME/livestreamer/plugins
Windows           %APPDATA%\\livestreamer\\plugins
================= ====================================================

.. note::

    If a plugin is added with the same name as a built-in plugin then
    the added plugin will take precedence. This is useful if you want
    to upgrade plugins independently of the Livestreamer version.


Playing built-in streaming protocols directly
---------------------------------------------

There are many types of streaming protocols used by services today and
Livestreamer supports most of them. It's possible to tell Livestreamer
to access a streaming protocol directly instead of relying on a plugin
to extract the streams from a URL for you.

A protocol can be accessed directly by specifying it in the URL format::

  protocol://path [key=value]

Accessing a stream that requires extra parameters to be passed along
(e.g. RTMP):

.. code-block:: console

    $ livestreamer "rtmp://streaming.server.net/playpath live=1 swfVfy=http://server.net/flashplayer.swf"


Most streaming technologies simply requires you to pass a HTTP URL, this is
a Adobe HDS stream:

.. code-block:: console

    $ livestreamer hds://streaming.server.net/playpath/manifest.f4m


Supported streaming protocols
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

============================== =================================================
Name                           Prefix
============================== =================================================
Adobe HTTP Dynamic Streaming   hds://
Akamai HD Adaptive Streaming   akamaihd://
Apple HTTP Live Streaming      hls:// hlsvariant://
Real Time Messaging Protocol   rtmp:// rtmpe:// rtmps:// rtmpt:// rtmpte://
Progressive HTTP, HTTPS, etc   httpstream://
============================== =================================================


.. _cli-options:

Command-line usage
------------------

.. code-block:: console

    $ livestreamer [OPTIONS] [URL] [STREAM]


.. argparse::
    :module: livestreamer_cli.argparser
    :attr: parser
