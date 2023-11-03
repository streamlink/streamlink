Quickstart
----------

This API is what powers the :ref:`CLI <cli:Command-Line Interface>`, but it's also available to developers that wish
to make use of the data Streamlink can retrieve in their own application.


Extracting streams
^^^^^^^^^^^^^^^^^^

The simplest use of the Streamlink API looks like this:

.. code-block:: python

    >>> import streamlink
    >>> streams = streamlink.streams("hls://devstreaming-cdn.apple.com/videos/streaming/examples/bipbop_4x3/bipbop_4x3_variant.m3u8")

This simply attempts to find a plugin and use it to extract streams from
the URL. This works great in simple cases but if you want more
fine tuning you need to use a `session object`_ instead.

The returned value is a dict containing :py:class:`Stream <streamlink.stream.Stream>` objects:

.. code-block:: python

    >>> streams
    {'41k': <HLSStream ['hls', 'https://devstreaming-cdn.apple.com/videos/streaming/examples/bipbop_4x3/gear0/prog_index.m3u8', 'https://devstreaming-cdn.apple.com/videos/streaming/examples/bipbop_4x3/bipbop_4x3_variant.m3u8']>,
     '230k': <HLSStream ['hls', 'https://devstreaming-cdn.apple.com/videos/streaming/examples/bipbop_4x3/gear1/prog_index.m3u8', 'https://devstreaming-cdn.apple.com/videos/streaming/examples/bipbop_4x3/bipbop_4x3_variant.m3u8']>,
     '650k': <HLSStream ['hls', 'https://devstreaming-cdn.apple.com/videos/streaming/examples/bipbop_4x3/gear2/prog_index.m3u8', 'https://devstreaming-cdn.apple.com/videos/streaming/examples/bipbop_4x3/bipbop_4x3_variant.m3u8']>,
     '990k': <HLSStream ['hls', 'https://devstreaming-cdn.apple.com/videos/streaming/examples/bipbop_4x3/gear3/prog_index.m3u8', 'https://devstreaming-cdn.apple.com/videos/streaming/examples/bipbop_4x3/bipbop_4x3_variant.m3u8']>,
     '1900k': <HLSStream ['hls', 'https://devstreaming-cdn.apple.com/videos/streaming/examples/bipbop_4x3/gear4/prog_index.m3u8', 'https://devstreaming-cdn.apple.com/videos/streaming/examples/bipbop_4x3/bipbop_4x3_variant.m3u8']>,
     'worst': <HLSStream ['hls', 'https://devstreaming-cdn.apple.com/videos/streaming/examples/bipbop_4x3/gear0/prog_index.m3u8', 'https://devstreaming-cdn.apple.com/videos/streaming/examples/bipbop_4x3/bipbop_4x3_variant.m3u8']>,
     'best': <HLSStream ['hls', 'https://devstreaming-cdn.apple.com/videos/streaming/examples/bipbop_4x3/gear4/prog_index.m3u8', 'https://devstreaming-cdn.apple.com/videos/streaming/examples/bipbop_4x3/bipbop_4x3_variant.m3u8']>}


If no plugin for the URL is found, a :py:exc:`NoPluginError <streamlink.exceptions.NoPluginError>` will be raised.
If an error occurs while fetching streams, a :py:exc:`PluginError <streamlink.exceptions.NoPluginError>` will be raised.


Opening streams to read data
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Now that you have extracted some streams we might want to read some data from
one of them. When you call :py:meth:`open() <streamlink.stream.Stream.open>` on a stream, a file-like object will be
returned, which you can call ``.read(size)`` and ``.close()`` on.


.. code-block:: python

    >>> fd = streams["best"].open()
    >>> data = fd.read(1024)
    >>> fd.close()

If an error occurs while opening a stream, a :py:exc:`StreamError <streamlink.exceptions.StreamError>` will be raised.


Inspecting streams
^^^^^^^^^^^^^^^^^^

It's also possible to inspect the stream's internal parameters. Go to
:ref:`Stream subclasses <api/stream:Stream>` to see which attributes are available
for inspection for each stream type.

For example, this is an :py:class:`HLSStream <streamlink.stream.HLSStream>` object which
contains a :py:attr:`url <streamlink.stream.HTTPStream.url>` attribute.

.. code-block:: python

    >>> streams["best"].url
    'https://devstreaming-cdn.apple.com/videos/streaming/examples/bipbop_4x3/gear4/prog_index.m3u8'


Session object
^^^^^^^^^^^^^^

The session allows you to set various options and is more efficient
when extracting streams more than once. You start by creating a
:py:class:`Streamlink <streamlink.session.Streamlink>` object:

.. code-block:: python

    >>> from streamlink import Streamlink
    >>> session = Streamlink()

You can then set options like this:

.. code-block:: python

    >>> session.set_option("stream-timeout", 30)

and extract streams like this:

.. code-block:: python

    >>> streams = session.streams("URL")


See :py:meth:`Streamlink.set_option() <streamlink.session.Streamlink.set_option>` to see which options are available.
