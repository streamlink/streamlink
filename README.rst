Livestreamer
============

.. image:: https://badge.fury.io/py/livestreamer.png
    :target: http://badge.fury.io/py/livestreamer

.. image:: https://secure.travis-ci.org/chrippa/livestreamer.png
    :target: http://travis-ci.org/chrippa/livestreamer

.. image:: https://pypip.in/d/livestreamer/badge.png
    :target: https://crate.io/packages/livestreamer?version=latest


Overview
--------

Livestreamer is a `command-line utility`_ that pipes video streams
from various services into a video player, such as `VLC <http://videolan.org/>`_.
The main purpose of Livestreamer is to allow the user to avoid buggy and CPU
heavy flash plugins but still be able to enjoy various streamed content.
There is also an `API`_ available for developers who want access
to the video stream data.

- Documentation: http://livestreamer.tanuki.se/
- Issue tracker: https://github.com/chrippa/livestreamer/issues
- PyPI: https://pypi.python.org/pypi/livestreamer
- Discussions: https://groups.google.com/forum/#!forum/livestreamer
- IRC: #livestreamer @ Freenode
- Free software: Simplified BSD license

.. _command-line utility: http://livestreamer.tanuki.se/en/latest/cli.html
.. _API: http://livestreamer.tanuki.se/en/latest/api_guide.html

Features
--------

Livestreamer is built upon a plugin system which allows support for new services
to be easily added. Currently most of the big streaming services are supported,
such as:

- `Dailymotion <http://dailymotion.com/live>`_
- `Livestream <http://livestream.com>`_
- `Twitch <http://twitch.tv>`_
- `YouTube Live <http://youtube.com>`_
- `UStream <http://ustream.tv>`_

... and many more. A full list of plugins currently included can be found
on the `Plugins`_ page.

.. _Plugins: http://livestreamer.tanuki.se/en/latest/plugin_matrix.html

Quickstart
-----------

The default behaviour of Livestreamer is to playback a stream in the default
player (`VLC <http://videolan.org/>`_).

.. sourcecode:: console

    # pip install livestreamer
    $ livestreamer twitch.tv/day9tv best
    [cli][info] Found matching plugin twitch for URL twitch.tv/day9tv
    [cli][info] Opening stream: source
    [cli][info] Starting player: vlc

For more in-depth usage and install instructions see the `User guide`_.

.. _User guide: http://livestreamer.tanuki.se/en/latest/index.html#user-guide

Related software
----------------

Feel free to add any Livestreamer related things to
the `wiki <https://github.com/chrippa/livestreamer/wiki/>`_.


Contributing
------------

If you wish to report a bug or contribute code, please take a look
at `CONTRIBUTING.rst <CONTRIBUTING.rst>`_ first.

