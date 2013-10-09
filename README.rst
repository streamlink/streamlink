Livestreamer
============

.. image:: https://badge.fury.io/py/livestreamer.png
    :target: http://badge.fury.io/py/livestreamer

.. image:: https://secure.travis-ci.org/chrippa/livestreamer.png
    :target: http://travis-ci.org/chrippa/livestreamer

.. image:: https://pypip.in/d/livestreamer/badge.png
    :target: https://crate.io/packages/livestreamer?version=latest

.. image:: docs/_static/flattr-badge.png
    :target: https://flattr.com/submit/auto?user_id=chrippa&url=https%3A%2F%2Fgithub.com%2Fchrippa%2Flivestreamer


Livestreamer is CLI program that extracts streams from various services and pipes them into
a video player of choice.

* Documentation: http://livestreamer.tanuki.se/
* Discussions: https://groups.google.com/forum/#!forum/livestreamer
* GitHub: https://github.com/chrippa/livestreamer
* PyPI: https://pypi.python.org/pypi/livestreamer
* Free software: Simplified BSD license


Features
--------

Livestreamer is built upon a plugin system which allows support for new services
to be easily added.

Currently most of the big streaming services are supported, e.g.
`Dailymotion <http://dailymotion.com/live/>`_,
`Livestream <http://livestream.com>`_,
`Justin.tv <http://justin.tv>`_,
`Twitch <http://twitch.tv/>`_,
`UStream <http://ustream.tv>`_ and
`YouTube Live <http://youtube.com/live/>`_.


Usage
-----

The default behaviour of Livestreamer is to feed a stream to your player
software (default is VLC).

.. code-block:: console

    # pip install livestreamer
    $ livestreamer twitch.tv/day9tv best
    [cli][info] Found matching plugin twitch for URL twitch.tv/day9tv
    [cli][info] Opening stream: source
    [cli][info] Starting player: vlc


For more in-depth usage and install instructions see the full documentation available
at http://livestreamer.tanuki.se/.


Related software
----------------

Feel free to add any Livestreamer related things to
the `wiki <https://github.com/chrippa/livestreamer/wiki/>`_.


Contributing
------------

If you wish to report a bug or contribute code, please take a look
at `CONTRIBUTING.rst <CONTRIBUTING.rst>`_ first.

