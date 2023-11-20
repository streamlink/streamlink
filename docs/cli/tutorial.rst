Tutorial
========

Introduction
------------

Streamlink is a command-line application, which means that the commands described
here should be typed into a terminal, or to be more precise, into a command-line shell.

On Windows, you have to open either the `Windows Terminal`_ (recommended), `PowerShell`_ or `Command Prompt`_ (discouraged).
On macOS, open the `Terminal <macOS Terminal_>`_ app, and if you're on Linux or BSD,
the terminal emulator depends on your desktop environment and its configuration.

The way Streamlink works is that it's only a means to extract and transport
the streams, and the playback is done by an external video player. Streamlink
works best with `VLC`_ or `mpv`_, which are also cross-platform, but other players
may be compatible too, see the :ref:`Players <players:Players>` page for a complete overview.


Getting started
---------------

Now to get into actually using Streamlink, let's say you want to watch the
stream located on ``https://www.twitch.tv/nasa``, you start off by telling Streamlink
where to attempt to extract streams from. This is done by setting the URL as the
first argument on the :command:`streamlink` command:

.. code-block:: console

    $ streamlink twitch.tv/nasa
    [cli][info] Found matching plugin twitch for URL twitch.tv/nasa
    Available streams: audio_only, 160p (worst), 360p, 480p, 720p60, 1080p60 (best)

.. note::
    You don't need to include the protocol when dealing with HTTP(s) URLs,
    e.g. just ``twitch.tv/nasa`` is enough and quicker to type.

.. caution::

    Depending on the command-line shell in use, any kind of command argument like the input URL for example
    may need to get quoted or escaped. See the `Shell syntax`_ section down below.


This command will tell Streamlink to attempt to extract streams from the URL
specified via its :ref:`plugins system <plugins:Plugins>` which is responsible for resolving streams from specific
streaming services. If it's successful, Streamlink will print out a list of available streams to choose from.

In addition to Streamlink's plugins system, direct stream URLs can be played via the
:ref:`supported streaming protocols <cli/protocols:Streaming protocols>`, which also support playback of local files
using the ``file://`` protocol. Relative file paths and absolute paths are supported. All path separators are ``/``,
even on Windows.

.. code-block:: console

    $ streamlink hls://file://C:/hls/playlist.m3u8
    [cli][info] Found matching plugin stream for URL hls://file://C:/hls/playlist.m3u8
    Available streams: 180p (worst), 272p, 408p, 554p, 818p, 1744p (best)


To select a stream and start playback, simply add the stream name as a second
argument to the :command:`streamlink` command:

.. code-block:: console

    $ streamlink twitch.tv/nasa 1080p60
    [cli][info] Found matching plugin twitch for URL twitch.tv/nasa
    [cli][info] Opening stream: 1080p60 (hls)
    [cli][info] Starting player: vlc

The stream you chose should now be playing in the player. It's a common use case
to just want to start the highest quality stream and not be bothered with what it's
named. To do this, just specify ``best`` as the stream name and Streamlink will
attempt to rank the streams and open the one of highest quality. You can also
specify ``worst`` to get the lowest quality.

Now that you have a basic grasp of how Streamlink works, you may want to look
into customizing it to your own needs, such as:

- Creating a :ref:`configuration file <cli/config:Configuration file>` of options you want to use.
- Setting up your player to cache some data before playing the stream to help avoiding buffering issues
  or reducing its default buffering values for being able to watch low-latency streams.


.. _Command Prompt: https://docs.microsoft.com/en-us/windows-server/administration/windows-commands/windows-commands
.. _PowerShell: https://docs.microsoft.com/en-us/powershell/
.. _Windows Terminal: https://docs.microsoft.com/en-us/windows/terminal/get-started
.. _macOS Terminal: https://support.apple.com/guide/terminal/welcome/mac
.. _VLC: https://videolan.org/
.. _mpv: https://mpv.io/


Shell syntax
------------

Depending on your used command-line shell and how you've entered the command,
input strings like the URL or other command arguments may need to get `escaped <escape-character_>`_ or quoted,
because command-line shells interpret and treat certain characters as special symbols which can alter the shell's behavior,
like characters for substituting/expanding strings, delimiting commands, path/file globbing, etc.

The most relevant characters (among others) for input URLs that can cause unexpected results are

- ``&``, ``;`` (command delimiting)
- ``$``, ``%`` (variable substitution)
- ``?``, ``*`` (path globbing)

The quoting and escaping behavior varies wildly between each shell and its configuration,
so please take a look at your shell's documentation about all the details, if you're unsure.

**Quoting and character escaping examples:**

URL: ``https://example/path?a=$one&b=%two%&c=*three*;&``

.. tab-set::

    .. tab-item:: POSIX compliant

        - `BASH manual <bash_>`_
        - `ZSH manual <zsh_>`_

        .. code-block:: sh

            streamlink 'https://example/path?a=$one&b=%two%&c=*three*;&'
            streamlink "https://example/path?a=\$one&b=%two%&c=*three*;&"
            streamlink https://example/path?a=\$one\&b=%two%\&c=*three*\;\&

    .. tab-item:: FISH

        - `FISH language documentation <fish_>`_

        .. code-block:: fish

            streamlink 'https://example/path?a=$one&b=%two%&c=*three*;&'
            streamlink "https://example/path?a=\$one&b=%two%&c=*three*;&"
            streamlink https://example/path\?a=\$one&b=%two%&c=\*three\*\;\&

    .. tab-item:: PowerShell

        - `PowerShell language specification <pwsh_>`_

        .. code-block:: pwsh

            streamlink 'https://example/path?a=$one&b=%two%&c=*three*;&'
            streamlink "https://example/path?a=`$one&b=%two%&c=*three*;&"
            streamlink https://example/path?a=`$one`&b=%two%`&c=*three*`;`&

    .. tab-item:: Windows Batch

        - `Escape characters, delimiters and quotes <batch-ss64_>`_
        - `Percent sign escaping <batch-so_>`_

        .. code-block:: bat

            streamlink "https://example/path?a=$one&b="%"two"%"&c=*three*;&"
            streamlink https://example/path?a=$one^&b=^%two^%^&c=*three*^;^&

.. _escape-character: https://en.wikipedia.org/wiki/Escape_character
.. _bash: https://www.gnu.org/software/bash/manual/bash.html
.. _zsh: https://zsh.sourceforge.io/Doc/Release/zsh_toc.html
.. _fish: https://fishshell.com/docs/current/language.html
.. _pwsh: https://learn.microsoft.com/en-us/powershell/scripting/lang-spec/chapter-02
.. _batch-ss64: https://ss64.com/nt/syntax-esc.html
.. _batch-so: https://stackoverflow.com/a/31420292
