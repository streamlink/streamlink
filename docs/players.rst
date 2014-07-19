.. _players:


Players
=======

Transport modes
---------------

There are three different modes of transporting the stream to the player.

====================== =========================================================
Name                   Description
====================== =========================================================
Standard input pipe    This is the default behaviour when there are no other
                       options specified.
Named pipe (FIFO)      Use the :option:`--player-fifo` option to enable.
HTTP                   Use the :option:`--player-http` or
                       :option:`--player-continuous-http` options to enable.
====================== =========================================================


Player compatibility
--------------------

This is a list of video players and their compatibility with the transport
modes.

===================================================== ========== ========== ====
Name                                                  Stdin Pipe Named Pipe HTTP
===================================================== ========== ========== ====
`Daum Pot Player <http://potplayer.daum.net>`_        No         No         Yes [1]_
`MPC-HC <http://mpc-hc.org/>`_                        Yes [2]_   No         Yes [1]_
`MPlayer <http://mplayerhq.hu>`_                      Yes        Yes        Yes
`MPlayer2 <http://mplayer2.org>`_                     Yes        Yes        Yes
`mpv <http://mpv.io>`_                                Yes        Yes        Yes
`VLC media player <http://videolan.org>`_             Yes        Yes        Yes
===================================================== ========== ========== ====

.. [1] :option:`--player-continuous-http` must be used.
       Using HTTP with players that rely on Windows' codecs to access HTTP
       streams may have a long startup time since Windows tend to do multiple
       HTTP requests and Livestreamer will attempt to open the stream for each
       request.
.. [2] Stdin requires MPC-HC 1.7 or newer.


Known issues and workarounds
----------------------------

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

VLC hangs when buffering and no playback starts
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Some versions of 64-bit VLC seem to be unable to read the stream created by
rtmpdump. Using the 32-bit version of VLC might help.

VLC fails to play with a error message
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
VLC version *2.0.1* and *2.0.2* contains a bug that prevents it from
reading data from standard input. This has been fixed in version *2.0.3*.


