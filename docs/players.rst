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
`QuickTime <http://apple.com/quicktime>`_             No         No         No
`VLC media player <http://videolan.org>`_             Yes [3]_   Yes        Yes
===================================================== ========== ========== ====

.. [1] :option:`--player-continuous-http` must be used.
       Using HTTP with players that rely on Windows' codecs to access HTTP
       streams may have a long startup time since Windows tend to do multiple
       HTTP requests and Streamlink will attempt to open the stream for each
       request.
.. [2] Stdin requires MPC-HC 1.7 or newer.

.. [3] Some versions of VLC might be unable to use the stdin pipe and
       prints the error message::

       VLC is unable to open the MRL 'fd://0'

       Use one of the other transport methods instead to work around this.


Known issues and workarounds
----------------------------

MPC-HC reports "File not found"
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Upgrading to version 1.7 or newer will solve this issue since reading data
from standard input is not supported in version 1.6.x of MPC-HC.

MPC-HC only plays sound on Twitch streams
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Twitch sometimes returns badly muxed streams which may confuse players. The
following workaround was contributed by MPC-HC developer @kasper93:

    *To fix this problem go to options -> internal filters -> open splitter
    settings and increase "Stream Analysis Duration" this will let ffmpeg to
    properly detect all streams.*

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
