Streamlink
==========

Overview
--------

Streamlink is a :ref:`command-line utility <cli:Command-Line Interface>` which pipes video streams
from various services into a video player, such as `VLC`_.
The main purpose of Streamlink is to avoid resource-heavy and unoptimized websites,
while still allowing the user to enjoy various streamed content.
There is also an :ref:`API <api_guide:API Guide>` available for developers who want access
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

Features
--------

Streamlink is built upon a plugin system which allows support for new services
to be easily added. Most of the big streaming services are supported, such as:

- `Twitch.tv <https://www.twitch.tv/>`_
- `YouTube.com <https://www.youtube.com/>`_
- `Livestream.com <https://livestream.com/>`_
- `Dailymotion.com <https://www.dailymotion.com/live>`_

... and many more. A full list of plugins currently included can be found
on the :ref:`Plugins <plugins:Plugins>` page.

Quickstart
----------

The default behavior of Streamlink is to play back streams in the `VLC <https://www.videolan.org/>`_ player.

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
- `Netlify <https://netlify.com/>`_, for hosting docs preview builds
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
    donate
    applications
    thirdparty
