API Reference
=============

This is a reference of all the available API methods in Streamlink.


Streamlink
------------

.. autofunction:: streamlink.streams


Session
-------

.. autoclass:: streamlink.Streamlink
    :member-order: bysource


Plugins
-------

Plugin
^^^^^^

.. module:: streamlink.plugin

.. autoclass:: Plugin
    :private-members: _get_streams
    :member-order: bysource

Plugin decorators
^^^^^^^^^^^^^^^^^

.. autodecorator:: pluginmatcher

.. autodecorator:: pluginargument

Plugin arguments
^^^^^^^^^^^^^^^^

.. module:: streamlink.options

.. autoclass:: Argument

.. autoclass:: Arguments


Streams
-------

.. module:: streamlink.stream

All streams inherit from the :class:`Stream` class.

Stream
^^^^^^

.. autoclass:: Stream

MuxedStream
^^^^^^^^^^^

.. autoclass:: MuxedStream

HTTPStream
^^^^^^^^^^

.. autoclass:: HTTPStream

HLSStream
^^^^^^^^^

.. autoclass:: HLSStream

MuxedHLSStream
^^^^^^^^^^^^^^

.. autoclass:: MuxedHLSStream

DASHStream
^^^^^^^^^^

.. autoclass:: DASHStream


Exceptions
----------

Streamlink has three types of exceptions:

.. autoexception:: streamlink.StreamlinkError
.. autoexception:: streamlink.PluginError
.. autoexception:: streamlink.NoPluginError
.. autoexception:: streamlink.StreamError
