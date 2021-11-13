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
`Daum Pot Player`_                                    Yes        No         Yes [1]_
`MPC-HC`_                                             Yes [2]_   No         Yes [1]_
`MPlayer`_                                            Yes        Yes        Yes
`mpv`_                                                Yes        Yes        Yes
`OMXPlayer`_                                          No         Yes        Yes [4]_
`QuickTime`_                                          No         No         No
`VLC media player`_                                   Yes [3]_   Yes        Yes
===================================================== ========== ========== ====

.. [1] :option:`--player-continuous-http` must be used.
       Using HTTP with players that rely on Windows' codecs to access HTTP
       streams may have a long startup time since Windows tend to do multiple
       HTTP requests and Streamlink will attempt to open the stream for each
       request.
.. [2] Stdin requires MPC-HC 1.7 or newer.

.. [3] Some versions of VLC might be unable to use the stdin pipe and
       prints the error message

       VLC is unable to open the MRL 'fd://0'

       Use one of the other transport methods instead to work around this.

.. [4] :option:`--player-continuous-http` has been reported to work for HLS
       streams when also using the timeout option for omxplayer
       (see `When using OMXPlayer the stream stops unexpectedly`_.)
       Other stream types may not work as expected, it is recommended that
       :option:`--player-fifo` be used.

.. _Daum Pot Player: https://potplayer.daum.net
.. _MPC-HC: https://mpc-hc.org/
.. _MPlayer: https://mplayerhq.hu
.. _mpv: https://mpv.io
.. _OMXPlayer: https://www.raspberrypi.org/documentation/raspbian/applications/omxplayer.md
.. _QuickTime: https://apple.com/quicktime
.. _VLC media player: https://videolan.org


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
This is a bug in MPlayer, using the MPlayer fork `mpv`_ instead
is recommended.

Youtube Live does not work with VLC
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
VLC versions below 3 cannot play Youtube Live streams. Please update your
player. You can also try using a different player.

Youtube Live does not work with Mplayer
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Some versions of Mplayer cannot play Youtube Live streams. And errors like:

.. code-block:: console

    Cannot seek backward in linear streams!
    Seek failed

Switching to a recent fork such as mpv resolves the issue.

When using OMXPlayer the stream stops unexpectedly
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
When reading from a fifo pipe OMXPlayer will quit when there is no data, to fix
this you can supply the timeout option to OMXPlayer using :option:`--player "omxplayer --timeout 20" <--player>`.
For live streams it might be beneficial to also add the omxplayer parameter ``--live``.
