.. _cli:

Command-Line Interface
======================

Tutorial
--------

Streamlink is command-line application, this means the commands described
here should be typed into a terminal. On Windows this means you should open
the `command prompt`_ or `PowerShell`_, on Mac OS X open the `Terminal`_ app
and if you're on Linux or BSD you probably already know the drill.

The way Streamlink works is that it's only a means to extract and transport
the streams, and the playback is done by an external video player. Streamlink
works best with `VLC`_ or `mpv`_, which are also cross-platform, but other players
may be compatible too, see the :ref:`Players` page for a complete overview.

Now to get into actually using Streamlink, let's say you want to watch the
stream located on http://twitch.tv/day9tv, you start off by telling Streamlink
where to attempt to extract streams from. This is done by giving the URL to the
command :command:`streamlink` as the first argument:

.. code-block:: console

    $ streamlink twitch.tv/day9tv
    [cli][info] Found matching plugin twitch for URL twitch.tv/day9tv
    Available streams: audio, high, low, medium, mobile (worst), source (best)


.. note::
    You don't need to include the protocol when dealing with HTTP URLs,
    e.g. just ``twitch.tv/day9tv`` is enough and quicker to type.


This command will tell Streamlink to attempt to extract streams from the URL
specified, and if it's successful, print out a list of available streams to choose
from.

To select a stream and start playback, we simply add the stream name as a second
argument to the :command:`streamlink` command:

.. sourcecode:: console

    $ streamlink twitch.tv/day9tv source
    [cli][info] Found matching plugin twitch for URL twitch.tv/day9tv
    [cli][info] Opening stream: source (hls)
    [cli][info] Starting player: vlc


The stream you chose should now be playing in the player. It's a common use case
to just want start the highest quality stream and not be bothered with what it's
named. To do this just specify ``best`` as the stream name and Streamlink will
attempt to rank the streams and open the one of highest quality. You can also
specify ``worst`` to get the lowest quality.

Now that you have a basic grasp of how Streamlink works, you may want to look
into customizing it to your own needs, such as:

- Creating a :ref:`configuration file <cli-streamlinkrc>` of options you
  want to use
- Setting up your player to :ref:`cache some data <issues-player_caching>`
  before playing the stream to help avoiding buffering issues


.. _command prompt: http://windows.microsoft.com/en-us/windows/command-prompt-faq#1TC=windows-8
.. _PowerShell: http://www.microsoft.com/powershell
.. _Terminal: http://en.wikipedia.org/wiki/Terminal_(OS_X)
.. _VLC: http://videolan.org/
.. _mpv: http://mpv.io/


.. _cli-streamlinkrc:

Configuration file
------------------

Writing the command-line options every time is inconvenient, that's why Streamlink
is capable of reading options from a configuration file instead.

Streamlink will look for config files in different locations depending on
your platform:

================= ====================================================
Platform          Location
================= ====================================================
Unix-like (POSIX) - $XDG_CONFIG_HOME/streamlink/config
                  - ~/.streamlinkrc
Windows           %APPDATA%\\streamlink\\streamlinkrc
================= ====================================================

You can also specify the location yourself using the :option:`--config` option.

.. note::

  - `$XDG_CONFIG_HOME` is ``~/.config`` if it has not been overridden
  - `%APPDATA%` is usually ``<your user directory>\Application Data``

.. note::

  On Windows there is a default config created by the installer but on any
  other platform you must create the file yourself.


Syntax
^^^^^^

The config file is a simple text file and should contain one
:ref:`command-line option <cli-options>` (omitting the dashes) per
line in the format::

  option=value

or for a option without value::

  option

.. note::
    Any quotes used will be part of the value, so only use when the value needs them,
    e.g. specifiying a player with a path containing spaces.

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

Streamlink expects this config to be named like the main config but
with ``.<plugin name>`` attached to the end.

Examples
^^^^^^^^

================= ====================================================
Platform          Location
================= ====================================================
Unix-like (POSIX) - $XDG_CONFIG_HOME/streamlink/config\ **.twitch**
                  - ~/.streamlinkrc\ **.ustreamtv**
Windows           %APPDATA%\\streamlink\\streamlinkrc\ **.youtube**
================= ====================================================

Have a look at the :ref:`list of plugins <plugin_matrix>` to see
the name of each built-in plugin.


Plugin specific usage
---------------------

Authenticating with Twitch
^^^^^^^^^^^^^^^^^^^^^^^^^^

It's possible to access subscription content on Twitch by giving Streamlink
access to your account.

Authentication is done by creating an OAuth token that Streamlink will
use to access your account. It's done like this:

.. sourcecode:: console

    $ streamlink --twitch-oauth-authenticate


This will open a web browser where Twitch will ask you if you want to give
Streamlink permission to access your account, then forwards you to a page
with further instructions on how to use it.


Authenticating with Crunchyroll
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Crunchyroll requires authenticating with a premium account to access some of
their content. To do so, the plugin provides a couple of options to input your
information, :option:`--crunchyroll-username` and :option:`--crunchyroll-password`.

You can login like this:

.. sourcecode:: console

    $ streamlink --crunchyroll-username=xxxx --crunchyroll-password=xxx http://crunchyroll.com/a-crunchyroll-episode-link

.. note::

    If you omit the password, streamlink will ask for it.

Once logged in, the plugin makes sure to save the session credentials to avoid
asking your username and password again.

Neverthless, these credentials are valid for a limited amount of time, so it
might be a good idea to save your username and password in your
:ref:`configuration file <cli-streamlinkrc>` anyway.

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

Streamlink will attempt to load standalone plugins from these directories:

================= ====================================================
Platform          Location
================= ====================================================
Unix-like (POSIX) $XDG_CONFIG_HOME/streamlink/plugins
Windows           %APPDATA%\\streamlink\\plugins
================= ====================================================

.. note::

    If a plugin is added with the same name as a built-in plugin then
    the added plugin will take precedence. This is useful if you want
    to upgrade plugins independently of the Streamlink version.


Playing built-in streaming protocols directly
---------------------------------------------

There are many types of streaming protocols used by services today and
Streamlink supports most of them. It's possible to tell Streamlink
to access a streaming protocol directly instead of relying on a plugin
to extract the streams from a URL for you.

A protocol can be accessed directly by specifying it in the URL format::

  protocol://path [key=value]

Accessing a stream that requires extra parameters to be passed along
(e.g. RTMP):

.. code-block:: console

    $ streamlink "rtmp://streaming.server.net/playpath live=1 swfVfy=http://server.net/flashplayer.swf"


Most streaming technologies simply requires you to pass a HTTP URL, this is
a Adobe HDS stream:

.. code-block:: console

    $ streamlink hds://streaming.server.net/playpath/manifest.f4m


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

    $ streamlink [OPTIONS] [URL] [STREAM]


.. argparse::
    :module: streamlink_cli.argparser
    :attr: parser
