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


Player specific issues
----------------------

MPC-HC reports "File not found"
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Upgrading to version 1.7 or newer will solve this issue since reading data
from standard input is not supported in version 1.6.x of MPC-HC.


MPC-HC only plays sound on Twitch streams
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Twitch sometimes returns badly muxed streams which may confuse players. The
following workaround was contributed by MPC-HC developer `kasper93 <https://github.com/kasper93>`_:

*To fix this problem go to options -> internal filters -> open splitter settings
and increase "Stream Analysis Duration" this will let ffmpeg to properly detect
all streams.*

Using :option:`--player-passthrough hls <--player-passthrough>` has also been
reported to work.

MPlayer tries to play Twitch streams at the wrong FPS
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This is a bug in MPlayer, using the MPlayer fork `mpv <http://mpv.io>`_ instead
is recommended.

VLC fails to play with a error message
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
VLC version *2.0.1* and *2.0.2* contains a bug that prevents it from
reading data from standard input. This has been fixed in version *2.0.3*.

VLC hangs when buffering and no playback starts
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Some versions of 64-bit VLC seem to be unable to read the stream created by rtmpdump.
Using the 32-bit version of VLC is a workaround until this bug is fixed.

