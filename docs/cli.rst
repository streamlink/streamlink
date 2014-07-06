.. _cli:

Command-Line Interface
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
    [cli][info] Found matching plugin twitch for URL twitch.tv/day9tv
    Available streams: audio, high, low, medium, mobile (worst), source (best)

Livestreamer will find out what streams are available and print them out for you to choose from. Simply give ``livestreamer``
the stream as the second argument and playback will start in your video player of choice.

The words printed next to stream names within a parantheses are synonyms and can be used when selecting stream to play.
In this case the ``best`` stream is a reference to the stream that is considered to be of highest quality, e.g ``source``.

.. sourcecode:: console

    $ livestreamer twitch.tv/day9tv best
    [cli][info] Found matching plugin twitch for URL twitch.tv/day9tv
    [cli][info] Opening stream: source
    [cli][info] Starting player: vlc

The default player is `VLC <http://videolan.org/>`_, but it can be easily changed using the :option:`--player` option.


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


You can also specify a location yourself using the :option:`--config` option.


The file should contain one option per line in the format ``option[=value]``, like this:

.. code-block:: bash

    player=mplayer -cache 2048
    player-no-close
    twitch-cookie=_twitch_session_id=xxxxxx; persistent=xxxxx;


For a list of all the supported options see :ref:`cli-options`.


Plugin specific configuration file
----------------------------------

You may want to to use specific settings for some plugins only. This
can be accomplished by placing those settings inside a plugin specific
config file. Options inside these config files will override the main
config file when a URL matching the plugin is used.

Livestreamer expects this config to be named like the main config but
with ``.<plugin name>`` attached to the end.

A few examples:

  - ``~/.config/livestreamer/config.twitch``
  - ``~/.livestreamerrc.ustreamtv``
  - ``%APPDATA%\livestreamer\livestreamerrc.youtube``

You can see which plugins are installed using the command ``livestreamer --plugins``.

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


Authenticating with Crunchyroll
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Crunchyroll requires authenticating with a premium account to access some of
their content. To do so, the plugin provides a couple of options to input your
information, :option:`--crunchyroll-username` and :option:`--crunchyroll-password`.

You can login like this:

.. sourcecode:: console

    $ livestreamer --crunchyroll-username=xxxx --crunchyroll-password=xxx http://crunchyroll.com/a-crunchyroll-episode-link...

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

A protocol can be accessed directly by specifying it in the URL format:: 

    protocol://path [key=value]

For example, to access a RTMP stream which requires parameters to be passed along to the stream:

.. code-block:: console

    $ livestreamer "rtmp://streaming.server.net/playpath live=1 swfVfy=http://server.net/flashplayer.swf"


Most streaming technologies simply requires you to pass a HTTP URL, this is an Adobe HDS stream:

.. code-block:: console

    $ livestreamer hds://http://streaming.server.net/playpath/manifest.f4m


Livestreamer currently supports these protocols:


============================== =================================================
Name                           Prefix
============================== =================================================
Adobe HTTP Dynamic Streaming   hds://
Akamai HD Adaptive Streaming   akamaihd://
Apple HTTP Live Streaming      hls:// hlvsvariant://
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
