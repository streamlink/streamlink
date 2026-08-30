Plugins
=======

This is a list of the currently built-in plugins and what URLs and features
they support. Streamlink's primary focus is live streams, so VOD support
is limited.

The purpose of having plugins is to allow users of Streamlink to input URLs
from specific websites or streaming services without knowing the actual stream
URLs or implementations, while also automatically setting up certain
HTTP session parameters or providing additional features via
:ref:`CLI arguments <cli:Plugin Options>`, like authentication, skipping ads,
enabling low latency streaming, etc.

In addition to the plugins listed below, any of the supported
:ref:`streaming protocols <cli/protocols:Streaming protocols>` can be played
directly, like for example HLS and DASH.


.. plugins::
