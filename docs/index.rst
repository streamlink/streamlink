.. livestreamer documentation master file, created by
   sphinx-quickstart on Fri Aug 24 00:12:10 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

livestreamer documentation
==================================

.. automodule:: livestreamer

Exceptions
----------

The :mod:`livstreamer` module defines three exceptions:

.. autoexception:: PluginError
.. autoexception:: NoPluginError
.. autoexception:: StreamError

The livestreamer session
------------------------
.. autoclass:: Livestreamer
    :members:


Plugins
-------
.. module:: livestreamer.plugins
.. autoclass:: Plugin
    :members:


Streams
-------
.. module:: livestreamer.stream
.. autoclass:: Stream
    :members:


Examples
--------

Fetching a streams data::

    from livestreamer import Livestreamer

    url = "http://twitch.tv/day9tv"
    livestreamer = Livestreamer()
    channel = livestreamer.resolve_url(url)
    streams = channel.get_streams()

    stream = streams["720p"]
    fd = stream.open()

    while True:
        data = fd.read(1024)
        if len(data) == 0:
            break

        # do something with data

    # All streams are not guaranteed to support .close()
    if hasattr(fd, "close"):
        fd.close()



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

