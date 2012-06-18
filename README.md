Livestreamer
============
Livestreamer is a CLI program that launches streams from various
streaming services in a custom video player.

Currently supported sites are:

* Justin.tv/Twitch.tv
* Own3d.tv
* SVTPlay
* UStream
* YouTube

Note: Justin.tv plugin requires rtmpdump with jtv token support (recent git).

Livestreamer is compatible with Python version >= 2.6 and >= 3.0.


Installing (Linux, OS X etc)
----------
Make sure you have Python and Python setuptools then run:

    $ sudo python setup.py install


Installing (Windows)
--------------------
1. Install Python
2. Install Python setuptools
3. Get rtmpdump and unpack it somewhere (rtmpdump-20110925-git-6230845-win32.zip from http://rtmpdump.mplayerhq.hu/ should work)
4. Add these paths to your Path environment variable:
  * [Python path]\
  * [Python path]\scripts\
  * [rtmpdump path]\ (or specify full path with --rtmpdump option)
  * [VLC/mplayer/other path]\ (or specify full path with --player option)

5. Open a command prompt and change directory to livestreamer source, then run:
    python setup.py install

Note: If you want to use VLC be aware there is currently a bug in version 2.0.1
that prevents stdin reading from working. Use 2.0.0 or a nightly build for now.


Using
-----
    $ livestreamer --help


Saving arguments AKA config file
--------------------------------
Livestreamer can read arguments from the file ~/.livestreamerrc.
A example file:

    player=mplayer
    jtv-cookie=_jtv3_session_id=arandomhash


Using livestreamer as a library
-------------------------------
Livestreamer is also a library. Short example:

    import livestreamer

    url = "http://twitch.tv/day9tv"
    channel = livestreamer.resolve_url(url)
    streams = channel.get_streams()

    stream = streams["720p"]
    fd = stream.open()

    while True:
        data = fd.read(1024)
        if len(data) == 0:
            break

        # do something with data

    fd.close()

