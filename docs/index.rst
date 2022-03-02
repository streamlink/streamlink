Streamlink[-27]
===============

Overview
--------

Streamlink is a :ref:`command-line utility <cli:Command-Line Interface>` which pipes video streams
from various services into a video player, such as `VLC`_.
The main purpose of Streamlink is to avoid resource-heavy and unoptimized websites,
while still allowing the user to enjoy various streamed content.
There is also an :ref:`API <api_guide:API Guide>` available for developers who want access
to the stream data.

Streamlink[-27] is a fork of the `Streamlink <https://github.com/streamlink/streamlink>`_ project.

The project extension [-27] indicates that this project continues to support python 2.7,
as the streamlink project has discontinued python 2.7 support as of version 1.7.0.

Releases (|version|)
    https://github.com/Billy2011/streamlink-27/releases
GitHub
    https://github.com/Billy2011/streamlink-27
Issue tracker
    https://github.com/streamlink/streamlink/issues
Free software
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

.. toctree::
    :maxdepth: 2

    Overview <self>
    install
    cli
    plugins
    players
    issues
    deprecations
    developing
    api_guide
    api
    changelog
    donate
    applications
    thirdparty
