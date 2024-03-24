:orphan:


Streamlink
==========

Synopsis
--------

.. code-block:: console

   streamlink [OPTIONS] <URL> [STREAM]


Examples
--------

.. code-block:: console

   streamlink --loglevel debug youtu.be/VIDEO-ID best
   streamlink --player mpv --player-args '--no-border --no-keepaspect-window' twitch.tv/CHANNEL 1080p60
   streamlink --player-external-http --player-external-http-port 8888 URL STREAM
   streamlink --output /path/to/file --http-timeout 60 URL STREAM
   streamlink --stdout URL STREAM | ffmpeg -i pipe:0 ...
   streamlink --http-header 'Authorization=OAuth TOKEN' --http-header 'Referer=URL' URL STREAM
   streamlink --hls-live-edge 5 --stream-segment-threads 5 'hls://https://host/playlist.m3u8' best
   streamlink --twitch-low-latency -p mpv -a '--cache=yes --demuxer-max-back-bytes=2G' twitch.tv/CHANNEL best


Options
-------

.. argparse::


Bugs
----

Please open a new issue on Streamlink's issue tracker on GitHub and use the appropriate issue forms:

https://github.com/streamlink/streamlink/issues


See also
--------

For more detailed information about config files, plugin sideloading, streaming protocols, proxy support, metadata,
or plugin specific stuff, please see Streamlink's online CLI documentation here:

https://streamlink.github.io/cli.html

The list of available plugins and their descriptions can be found here:

https://streamlink.github.io/plugins.html
