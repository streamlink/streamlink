.. _api:

API
===

.. module:: livestreamer

This API is what powers the :ref:`cli` but is also available to developers that wish
to make use of the data Livestreamer can retrieve in their own application.


Tutorial
--------

You start by creating a :class:`Livestreamer` object, this object keeps track of
options and loads plugins.

.. code-block:: python

    >>> from livestreamer import Livestreamer
    >>> livestreamer = Livestreamer()

Next you should give a URL to livestreamer to see if a plugin is available for it.

If no plugin for the URL is found, a :exc:`NoPluginError` will be raised.

.. code-block:: python

    >>> plugin = livestreamer.resolve_url("http://twitch.tv/day9tv")


Now that you have a plugin, you can fetch the current streams.
The returned value is a dict containing :class:`Stream` objects.

If an error occurs while fetching streams, a :exc:`PluginError` will be raised.

.. code-block:: python

    >>> streams = plugin.get_streams()
    >>> streams
    {'720p': <livestreamer.stream.rtmpdump.RTMPStream object at 0x7fd94eb02050>, ... }


Now you can open a connection to a stream. When you call .open() on a stream,
a file-like object will be returned, which you can call .read(size) and .close() on.

If an error occurs while opening a stream, a :exc:`StreamError` will be raised.

.. code-block:: python

    >>> stream = streams.get("720p")
    >>> fd = stream.open()
    >>> data = fd.read(1024)
    >>> fd.close()


It's also possible to inspect streams internal parameters, see the relevant stream
class to see what properties are available for inspection.

For example this is a :class:`RTMPStream` object which contains a `params` property.

.. code-block:: python

    >>> stream.params
    {'jtv': '9571e0f58ecadd84f34010e8b87edbc19edc68fb ...', 
     'swfVfy': 'http://www-cdn.jtvnw.net/widgets/live_embed_player.r546689b07788ad27459b3e7add5ff4f7da1bf730.swf',
     'live': True, 'rtmp': 'rtmp://199.9.255.201/app/jtv_s08_tXsNkrA91g0Q'}

Session
-------

.. autoclass:: Livestreamer
    :members:


Plugins
-------
.. module:: livestreamer.plugin
.. autoclass:: Plugin
    :members:


Streams
-------

All streams inherit from the :class:`Stream` class.

.. module:: livestreamer.stream
.. autoclass:: Stream
    :members:


Stream subclasses
^^^^^^^^^^^^^^^^^

You are able to inspect the parameters used by each stream,
different properties are available depending on stream type.

.. autoclass:: AkamaiHDStream
    :members:

.. autoclass:: HDSStream
    :members:

.. autoclass:: HLSStream
    :members:

.. autoclass:: HTTPStream
    :members:

.. autoclass:: RTMPStream
    :members:


Exceptions
----------

Livestreamer has three types of exceptions:

.. autoexception:: livestreamer.LivestreamerError
.. autoexception:: livestreamer.PluginError
.. autoexception:: livestreamer.NoPluginError
.. autoexception:: livestreamer.StreamError


Examples
--------

Simple player
^^^^^^^^^^^^^

This example uses the Python bindings of `GStreamer <http://gstreamer.freedesktop.org/>`_
to playback a stream.

.. literalinclude:: ../examples/gst-player.py
