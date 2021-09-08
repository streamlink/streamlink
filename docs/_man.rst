:orphan:


Streamlink
==========

Synopsis
--------

.. code-block:: console

   streamlink [OPTIONS] <URL> [STREAM]

   streamlink --loglevel debug youtu.be/VIDEO-ID best
   streamlink --player mpv --player-args '--no-border --no-keepaspect-window' twitch.tv/CHANNEL 1080p60
   streamlink --player-external-http --player-external-http-port 8888 URL STREAM
   streamlink --output /path/to/file --http-timeout 60 URL STREAM
   streamlink --stdout URL STREAM | ffmpeg -i pipe:0 ...
   streamlink --http-header 'Authorization=OAuth TOKEN' --http-header 'Referer=URL' URL STREAM
   streamlink --hls-live-edge 5 --stream-segment-threads 5 'hls://https://host/playlist.m3u8' best
   streamlink --twitch-low-latency -p mpv -a '--cache=yes --demuxer-max-bytes=750k' twitch.tv/CHANNEL best


Options
=======

.. argparse::
    :module: streamlink_cli.main
    :attr: parser_helper
