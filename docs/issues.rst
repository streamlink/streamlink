.. _issues:

Common issues
=============

.. _issues-player_caching:

Streams are buffering/lagging
-----------------------------

Enable caching in your player
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

By default most players do not cache the data they receive from Streamlink.
Caching can reduce the amount of buffering you run into because the player will
have some breathing room between receiving the data and playing it.

============= ======================== ======================================
Player        Parameter                Note
============= ======================== ======================================
MPC-HC        --                       Currently no way of configuring the cache
MPlayer       ``-cache <kbytes>``      Between 1024 and 8192 is recommended
MPlayer2      ``-cache <kbytes>``      Between 1024 and 8192 is recommended
mpv           ``--cache <kbytes>``     Between 1024 and 8192 is recommended
VLC           ``--file-caching <ms>    Between 1000 and 10000 is recommended
              --network-caching <ms>``
============= ======================== ======================================

Use the :option:`--player` option to pass these options to your player.


Multi-threaded streaming
^^^^^^^^^^^^^^^^^^^^^^^^

On segmented streaming protocols (such as HLS and HDS) it's possible to use
multiple threads to potentially increase the throughput.
Each stream type has its own option, and these are the ones that are currently available:

=================================== ============================================
Option                              Used by these plugins
=================================== ============================================
:option:`--hls-segment-threads`     `twitch`, `youtube` and many more.
:option:`--hds-segment-threads`     `dailymotion`, `mlgtv` and many more.
:option:`--stream-segment-threads`  `ustreamtv`, `beattv` and any other plugins
                                    implementing their own segmented streaming
                                    protocol.
=================================== ============================================

.. note::

    Using 2 or 3 threads should be enough to see an impact on live streams,
    any more will likely not show much effect.
