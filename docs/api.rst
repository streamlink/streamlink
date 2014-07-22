.. _api:

API Reference
=============

.. module:: livestreamer

This ia reference of all the available API methods in Livestreamer.

Livestreamer
------------

.. autofunction:: streams


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


.. _api-stream-subclasses:

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

