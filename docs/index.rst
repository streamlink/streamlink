.. livestreamer documentation master file, created by
   sphinx-quickstart on Fri Aug 24 00:12:10 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.


What is Livestreamer?
---------------------

Livestreamer is a :ref:`cli` that pipes video streams from various services into a video player,
such as `VLC <http://videolan.org/>`_. The main purpose of Livestreamer is to allow the user to avoid buggy
and CPU heavy flash plugins but still be able to enjoy various streamed content.

There is also an :ref:`api` available for developers who want access to the video stream data.


Latest release: v\ |version| (:ref:`changelog`)

Features
--------

Livestreamer is built upon a plugin system which allows support for new services to be easily added.
Currently most of the big streaming services are supported, such as:

- `Dailymotion <http://dailymotion.com/live/>`_
- `Livestream <http://livestream.com>`_
- `Twitch <http://twitch.tv/>`_/`Justin.tv <http://justin.tv>`_
- `YouTube Live <http://youtube.com/live/>`_
- `UStream <http://ustream.tv>`_

And many more, a full list of plugins currently included can be found in the :ref:`plugin_matrix`.

Quickstart
-----------

The default behaviour of Livestreamer is to playback a stream in the default player (`VLC <http://videolan.org/>`_).

.. sourcecode:: console

    # pip install livestreamer
    $ livestreamer twitch.tv/day9tv best
    [cli][info] Found matching plugin justintv for URL twitch.tv/day9tv
    [cli][info] Opening stream: 720p
    [cli][info] Starting player: vlc

For more in-depth usage and install instructions see the `User guide`_.

User guide
----------

Livestreamer is made up of two parts, a basic :ref:`cli` and a library :ref:`api`.
See their respective sections for more information on how to use them.

.. toctree::
    :maxdepth: 2


    install
    cli
    issues
    api

