.. _issues:

Common issues
=============

Problems playing Twitch/Justin.tv streams
-----------------------------------------

This is probably caused by a outdated version of rtmpdump.

On Debian/Ubuntu it is recommended to use the official packages
of *librtmp0* and *rtmpdump* version *2.4+20111222.git4e06e21* or newer.
This version contains the necessary code to play Twitch/Justin.tv streams.

If you are building rtmpdump yourself it may link with a existing
(probably older) version of librtmp. You can avoid this by building
a static version of rtmpdump, using this make command:

.. code-block:: console

    $ make SHARED=


VLC fails to play with a error message
--------------------------------------

VLC version *2.0.1* and *2.0.2* contains a bug that prevents it from
reading data from standard input. This has been fixed in version *2.0.3*.


VLC hangs when buffering and no playback starts
-----------------------------------------------

Some versions of 64-bit VLC seem to be unable to read the stream created by rtmpdump.

Using the 32-bit version of VLC is a workaround until this bug is fixed.


Streams are buffering/lagging
-----------------------------

By default most players do not cache the input from stdin, here is a few command arguments you can pass to some common players:

- ``mplayer --cache <kbytes>`` (between 1024 and 8192 is recommended)
- ``vlc --file-caching <milliseconds>`` (between 1000 and 10000 is recommended)

These options can be used by passing ``--player`` to ``livestreamer``.

