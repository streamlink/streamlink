.. livestreamer documentation master file, created by
   sphinx-quickstart on Fri Aug 24 00:12:10 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

livestreamer documentation
==================================

Livestreamer is a library that can be used to retrieve information and stream data from
various livestreaming services, such as Twitch, Own3D or UStream.


.. automodule:: livestreamer

Exceptions
----------

The :mod:`livstreamer` module defines four exceptions:

.. exception:: PluginError

    Common base class for the plugin related exceptions. It inherits
    :exc:`Exception`.

.. exception:: NoPluginError

    This exception is triggered when no plugin can found when calling :meth:`Livestreamer.resolve_url`.
    It inherits :exc:`PluginError`.

.. exception:: StreamError

    Common base class for stream related exceptions. It inherits
    :exc:`Exception`.

The livestreamer session
------------------------
.. autoclass:: Livestreamer
    :members:

.. automodule:: livestreamer.plugins

Plugins
-------
.. autoclass:: Plugin
    :members:

.. automodule:: livestreamer.stream


Streams
-------
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

