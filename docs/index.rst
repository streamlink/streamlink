Streamlink
==========

Overview
--------

Streamlink is a :ref:`command-line utility <cli:Command-Line Interface>` which pipes video streams
from various services into a video player, such as `VLC`_ or `mpv`_.
The main purpose of Streamlink is to avoid resource-heavy and unoptimized websites,
while still allowing the user to enjoy various streamed content.
There is also a :ref:`Python API <api:API Reference>` available for developers who want access
to the stream data.

This project was forked from Livestreamer, which is no longer maintained.

:octicon:`tag` Latest release (|version|)
    https://github.com/streamlink/streamlink/releases/latest
:octicon:`mark-github` GitHub
    https://github.com/streamlink/streamlink
:octicon:`issue-opened` Issue tracker
    https://github.com/streamlink/streamlink/issues
:octicon:`comment-discussion` Discussion forum
    https://github.com/streamlink/streamlink/discussions
:octicon:`comment-discussion` Gitter/Matrix channel
    `streamlink/streamlink:gitter.im <https://matrix.to/#/#streamlink_streamlink:gitter.im>`_
:octicon:`package` PyPI
    https://pypi.org/project/streamlink/
:octicon:`law` Free software
    Simplified BSD license

.. _VLC: https://www.videolan.org/
.. _mpv: https://mpv.io/

Features
--------

Streamlink is built on top of a plugin system which allows support for new services to be added easily.
Most of the popular streaming services are supported, such as
`Twitch <https://www.twitch.tv/>`_, `YouTube <https://www.youtube.com/>`_, and many more.

A list of all plugins currently included can be found on the :ref:`plugins <plugins:Plugins>` page.

Quickstart
----------

The default behavior of Streamlink is to play back streams in the `VLC`_ player.

.. sourcecode:: console

    $ streamlink twitch.tv/day9tv best
    [cli][info] Found matching plugin twitch for URL twitch.tv/day9tv
    [cli][info] Available streams: audio_only, 160p (worst), 360p, 480p, 720p, 720p60, 1080p60 (best)
    [cli][info] Opening stream: 1080p60 (hls)
    [cli][info] Starting player: vlc

For more in-depth usage and install instructions, please refer to the `User guide`_.

User guide
----------

Streamlink is made up of two parts, a :ref:`cli <cli:Command-Line Interface>` and a library :ref:`API <api:API Reference>`.
See their respective sections for more information on how to use them.

Thank you
---------

- `Github <https://github.com/>`_, for hosting the git repo, docs, release assets and providing CI tools
- `Whatismybrowser <https://whatismybrowser.com>`_, for the access to their user-agents API in our CI workflows


Table of contents
-----------------

.. toctree::
    :maxdepth: 2

    Overview <self>
    install
    cli
    plugins
    players
    deprecations
    migrations
    developing
    api_guide
    api
    changelog
    support
    applications
    thirdparty
