Streaming protocols
===================

There are many types of streaming protocols used by services today and
Streamlink supports most of them. It's possible to tell Streamlink
to access a streaming protocol directly instead of relying on a plugin
to extract the streams from a URL for you.


Playing built-in streaming protocols directly
---------------------------------------------

A streaming protocol can be accessed directly by specifying it in the ``protocol://URL`` format
with an optional list of parameters, like so:

.. code-block:: console

    $ streamlink "protocol://https://streamingserver/path key1=value1 key2=value2"

Depending on the input URL, the explicit protocol scheme may be omitted.
The following example shows HLS streams (``.m3u8``) and DASH streams (``.mpd``):

.. code-block:: console

    $ streamlink "https://streamingserver/playlist.m3u8"
    $ streamlink "https://streamingserver/manifest.mpd"


Supported streaming protocols
-----------------------------

.. list-table::
    :header-rows: 1
    :class: table-custom-layout

    * - Name
      - Explicit prefix
    * - Apple HTTP Live Streaming
      - ``hls://``
    * - MPEG-DASH
      - ``dash://``
    * - Progressive HTTP/HTTPS
      - ``httpstream://``

.. note::

   Local files can be read by adding the ``file://`` scheme to the ``URL`` component.


Protocol parameters
-------------------

When passing parameters to the built-in streaming protocols, the values will either be treated as plain strings
or they will be interpreted as Python literals:

.. code-block:: console

    $ streamlink "httpstream://https://streamingserver/path method=POST params={'abc':123} json=['foo','bar','baz']"

.. code-block:: python

    method="POST"
    params={"key": 123}
    json=["foo", "bar", "baz"]

The parameters from the example above are used to make an HTTP ``POST`` request with ``abc=123`` added
to the query string and ``["foo", "bar", "baz"]`` used as the content of the HTTP request's body (the serialized JSON data).

Some parameters allow you to configure the behavior of the streaming protocol implementation directly:

.. code-block:: console

    $ streamlink "hls://https://streamingserver/path start_offset=123 duration=321 force_restart=True"


Available parameters
--------------------

Parameters are passed to the following methods of their respective stream implementations:

.. list-table::
    :header-rows: 1
    :class: table-custom-layout

    * - Protocol prefix
      - Method references
    * - ``httpstream://``
      - - :py:meth:`streamlink.stream.HTTPStream`
        - :py:meth:`requests.Session.request`
    * - ``hls://``
      - - :py:meth:`streamlink.stream.HLSStream.parse_variant_playlist`
        - :py:meth:`streamlink.stream.HLSStream`
        - :py:meth:`streamlink.stream.MuxedHLSStream`
        - :py:meth:`requests.Session.request`
    * - ``dash://``
      - - :py:meth:`streamlink.stream.DASHStream.parse_manifest`
        - :py:meth:`requests.Session.request`
