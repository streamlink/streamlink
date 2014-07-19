.. _issues:

Common issues
=============

.. _issues-player_caching:

Streams are buffering/lagging
-----------------------------
By default most players do not cache the data they receieve from Livestreamer.
Caching can reduce the amount of buffering you run into because the player will 
have some breathing room between receving the data and playing it.

How to enable cache in the most common players
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

============= ======================== ======================================
Player        Parameter                Note
============= ======================== ======================================
MPC-HC        --                       Currently no way of configuring the cache
MPlayer       ``-cache <kbytes>``      Between 1024 and 8192 is recommended
MPlayer2      ``-cache <kbytes>``      Between 1024 and 8192 is recommended
mpv           ``--cache <kbytes>``     Between 1024 and 8192 is recommended
VLC           ``--file-caching         Between 1000 and 10000 is recommended
              <milliseconds>
              --network-caching
              <milliseconds>``
============= ======================== ======================================

Use the :option:`--player` option to pass these options to your player.


