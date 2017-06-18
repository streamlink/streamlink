.. _api:

API Reference
=============

.. module:: streamlink

This ia reference of all the available API methods in Streamlink.

Streamlink
------------

.. autofunction:: streams


Session
-------

.. autoclass:: Streamlink
    :members:


Plugins
-------
.. module:: streamlink.plugin
.. autoclass:: Plugin
    :members:


Streams
-------

All streams inherit from the :class:`Stream` class.

.. module:: streamlink.stream
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

Streamlink has three types of exceptions:

.. autoexception:: streamlink.StreamlinkError
.. autoexception:: streamlink.PluginError
.. autoexception:: streamlink.NoPluginError
.. autoexception:: streamlink.StreamError
