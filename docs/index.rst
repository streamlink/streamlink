Overview
--------

Streamlink is a :ref:`command-line utility <cli>` that pipes video streams
from various services into a video player, such as `VLC <http://videolan.org/>`_.
The main purpose of Streamlink is to allow the user to avoid buggy and CPU
heavy flash plugins but still be able to enjoy various streamed content.
There is also an :ref:`API <api_guide>` available for developers who want access
to the video stream data. This project was forked from Livestreamer, which is
no longer maintained.

- Latest release: |version| (:ref:`changelog`)
- GitHub: https://github.com/streamlink/streamlink
- Issue tracker: https://github.com/streamlink/streamlink/issues
- PyPI: https://pypi.python.org/pypi/streamlink
- Free software: Simplified BSD license

Features
--------

Streamlink is built upon a plugin system which allows support for new services
to be easily added. Currently most of the big streaming services are supported,
such as:

- `Dailymotion <http://dailymotion.com/live>`_
- `Livestream <http://livestream.com>`_
- `Twitch <http://twitch.tv>`_
- `UStream <http://ustream.tv>`_
- `YouTube Live <http://youtube.com>`_

... and many more. A full list of plugins currently included can be found
on the :ref:`plugin_matrix` page.

Quickstart
-----------

The default behaviour of Streamlink is to playback a stream in the default
player (`VLC <http://videolan.org/>`_).

.. sourcecode:: console

    # pip install streamlink
    $ streamlink twitch.tv/day9tv best
    [cli][info] Found matching plugin twitch for URL twitch.tv/day9tv
    [cli][info] Opening stream: source (hls)
    [cli][info] Starting player: vlc

For more in-depth usage and install instructions see the `User guide`_.

User guide
----------

Streamlink is made up of two parts, a :ref:`cli` and a library :ref:`API <api>`.
See their respective sections for more information on how to use them.

.. toctree::
    :maxdepth: 2

    install
    cli
    plugin_matrix
    players
    issues
    api_guide
    api
