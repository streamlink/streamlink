Livestreamer
============

.. image:: http://img.shields.io/pypi/v/livestreamer.svg?style=flat-square
    :target: https://pypi.python.org/pypi/livestreamer

.. image:: http://img.shields.io/pypi/dm/livestreamer.svg?style=flat-square
    :target: https://pypi.python.org/pypi/livestreamer

.. image:: http://img.shields.io/travis/chrippa/livestreamer.svg?style=flat-square
    :target: http://travis-ci.org/chrippa/livestreamer



Overview
--------

Livestreamer is a `command-line utility`_ that pipes video streams
from various services into a video player, such as `VLC <http://videolan.org/>`_.
The main purpose of Livestreamer is to allow the user to avoid buggy and CPU
heavy flash plugins but still be able to enjoy various streamed content.
There is also an `API`_ available for developers who want access
to the video stream data.

- Documentation: http://docs.livestreamer.io/
- Issue tracker: https://github.com/chrippa/livestreamer/issues
- PyPI: https://pypi.python.org/pypi/livestreamer
- Discussions: https://groups.google.com/forum/#!forum/livestreamer
- IRC: #livestreamer @ Freenode
- Free software: Simplified BSD license

.. _command-line utility: http://docs.livestreamer.io/cli.html
.. _API: http://docs.livestreamer.io/api_guide.html

Features
--------

Livestreamer is built upon a plugin system which allows support for new services
to be easily added. Currently most of the big streaming services are supported,
such as:

- `Dailymotion <http://dailymotion.com/live>`_
- `Livestream <http://livestream.com>`_
- `Twitch <http://twitch.tv>`_
- `UStream <http://ustream.tv>`_
- `YouTube Live <http://youtube.com>`_

... and many more. A full list of plugins currently included can be found
on the `Plugins`_ page.

.. _Plugins: http://docs.livestreamer.io/plugin_matrix.html

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

.. _User guide: http://docs.livestreamer.io/index.html#user-guide

Related software
----------------

Feel free to add any Livestreamer related things to
the `wiki <https://github.com/chrippa/livestreamer/wiki/>`_.


Contributing
------------

If you wish to report a bug or contribute code, please take a look
at `CONTRIBUTING.rst <CONTRIBUTING.rst>`_ first.

