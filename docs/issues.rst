Common issues
=============

Streams are buffering/lagging
-----------------------------

Enable caching in your player
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

By default most players do not cache the data they receive from Streamlink.
Caching can reduce the amount of buffering you run into because the player will
have some breathing room between receiving the data and playing it.

============= ============================== ======================================
Player        Parameter                      Note
============= ============================== ======================================
MPC-HC        --                             Currently no way of configuring the cache
MPlayer       ``-cache <kbytes>``            Between 1024 and 8192 is recommended
mpv           ``--cache=yes                  Between 1024 and 8192 is recommended
              --demuxer-max-bytes=<kbytes>``
VLC           ``--file-caching <ms>          Between 1000 and 10000 is recommended
              --network-caching <ms>``
============= ============================== ======================================

Use the :option:`--player-args` or :option:`--player` option to pass these options to your player.


Multi-threaded streaming
^^^^^^^^^^^^^^^^^^^^^^^^

On segmented streaming protocols (such as HLS and DASH) it's possible to use
multiple threads for downloading multiple segments at the same time to
potentially increase the throughput. This can be done via Streamlink's
:option:`--stream-segment-threads` argument.

.. note::

    Using 2 or 3 threads should be enough to see an impact on live streams,
    any more will likely not show much effect.
