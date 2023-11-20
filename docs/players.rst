Players
=======

Transport modes
---------------

There are three different modes of transporting the stream to the player.

.. list-table::
    :header-rows: 1
    :class: sd-w-100

    * - Name
      - Description
    * - Standard input pipe
      - This is the default behavior when there are no other options specified.
    * - Named pipe (FIFO)
      - See the :option:`--player-fifo` option.
    * - HTTP
      - See the :option:`--player-http` and :option:`--player-continuous-http` options.

.. note::

    Streamlink also allows passing the resolved stream URL through to the player as its first launch argument
    when using the :option:`--player-passthrough` option.

    This does only work if the player has support the specific streaming protocol built in. The player will then do
    all the data fetching on its own while Streamlink will just wait for the player process to end.

    Some streaming protocols like DASH can't be passed through to the player.


Player compatibility
--------------------

This is a list of video players and their compatibility with the transport
modes.

.. list-table::
    :header-rows: 1
    :class: sd-w-100

    * - Name
      - OS
      - License
      - stdin pipe
      - named pipe
      - HTTP
    * - `VLC media player`_
      - :fab:`windows;fa-xl` :fab:`apple;fa-xl` :fab:`linux;fa-xl`
      - GPL2 / LGPL2.1
      - :octicon:`thumbsup;1em;sd-text-success` [1]_
      - :octicon:`thumbsup;1em;sd-text-success`
      - :octicon:`thumbsup;1em;sd-text-success`
    * - `mpv`_
      - :fab:`windows;fa-xl` :fab:`apple;fa-xl` :fab:`linux;fa-xl`
      - GPL2 / LGPL2.1
      - :octicon:`thumbsup;1em;sd-text-success`
      - :octicon:`thumbsup;1em;sd-text-success`
      - :octicon:`thumbsup;1em;sd-text-success`
    * - `MPlayer`_
      - :fab:`windows;fa-xl` :fab:`apple;fa-xl` :fab:`linux;fa-xl`
      - GPL2
      - :octicon:`thumbsup;1em;sd-text-success`
      - :octicon:`thumbsup;1em;sd-text-success`
      - :octicon:`thumbsup;1em;sd-text-success`
    * - `IINA`_
      - :fab:`apple;fa-xl`
      - GPL3
      - :octicon:`thumbsup;1em;sd-text-success` [2]_
      - :octicon:`thumbsdown;1em;sd-text-danger`
      - :octicon:`thumbsdown;1em;sd-text-danger`

.. [1] Some versions of VLC might be unable to use the stdin pipe and
       prints the error message

       VLC is unable to open the MRL 'fd://0'

       Use one of the other transport methods instead to work around this.

.. [2] Requires the ``--stdin`` player argument (:option:`--player-args`)

.. _VLC media player: https://videolan.org/
.. _mpv: https://mpv.io/
.. _MPlayer: https://mplayerhq.hu/
.. _IINA: https://iina.io/


Known issues and workarounds
----------------------------

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
