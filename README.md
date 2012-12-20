Livestreamer
============
Livestreamer is a CLI program that launches live streams from various streaming
services in a custom video player and also a Python library that allows you to
interact with the stream data in your own application.

Current release: **1.4.1** (2012-12-20). See [CHANGELOG](https://github.com/chrippa/livestreamer/blob/master/CHANGELOG) for release notes.

Currently includes plugins for these sites:

* Dailymotion
* GOMTV.net (live and VOD)
* livestream.com and new.livestream.com
* ongamenet.com
* own3D.tv
* SVTPlay (live and VOD)
* Twitch/Justin.tv
* UStream
* YouTube

... and many more. See ```livestreamer --plugins``` for the full list!


Installing
---------------------------
**UNIX-like OSes**
Pip is a tool to install Python packages from a central repository.

    sudo pip install livestreamer

**Windows**
Download the installer from the [Downloads](https://github.com/chrippa/livestreamer/downloads) section.

*Note!* If you have previously installed manually you may need to remove ```livestreamer.exe``` from ```PYTHONPATH\Scripts```.


Using
-----
Livestreamer is command line interface, you must use it from a terminal/command prompt.

See ```livestreamer --help``` for all the options and usage.


Saving arguments
--------------------------------
Livestreamer can read arguments from the file ```~/.livestreamerrc``` (UNIX-like) or ```%APPDATA%\livestreamer\livestreamerrc``` (Windows).
The file should contain an argument per line, like this:

    player=mplayer -cache 2048
    gomtv-username=username
    gomtv-password=password


Plugin specific usage
---------------------
Most plugins are straight-forward to use, just pass the URL to the stream and it will work.
However, some plugins are using what could be called a "meta URL" to find the stream for you.

* **gomtv** Passing the URL *gomtv.net* will make the plugin figure out what match is currently playing automatically.
* **ongamenet** To use this plugin the URL *ongamenet.com* must be passed. 


Common issues
-------------
**livestreamer errors with "Unable to read from stream" or "Error while executing subprocess" on Twitch/JustinTV streams.**

When building rtmpdump from source it may link with a already existing (probably older) librtmp version instead of using it's
own version. On Debian/Ubuntu it is recommended to use the official packages of ```librtmp0``` and ```rtmpdump``` version
```2.4+20111222.git4e06e21``` or newer. This version contains the necessary code to play Twitch/JustinTV streams and
avoids any conflicts. It should be available in the testing or unstable repositories if it's not available in stable yet.

**VLC fails to play with a error message.**

VLC version ```2.0.1``` and ```2.0.2``` contains a bug that prevents it from reading data from standard input.
This has been fixed in version ```2.0.3```.

**Streams are buffering/lagging**

By default most players do not cache the input from stdin, here is a few command arguments you can pass to some common players:

* ```mplayer --cache <kbytes>``` (between 1024 and 8192 is recommended)
* ```vlc --file-caching <milliseconds>``` (between 1000 and 10000 is recommended)

These arguments can be used by passing --player to livestreamer.


Installing (Manual)
---------------------------------

**UNIX like OSes** From the source tree run:

    sudo python setup.py install

**Windows**

1. Install Python
2. Install Python setuptools
3. Get rtmpdump and unpack it somewhere (rtmpdump-20110925-git-6230845-win32.zip from the downloads section should work)
4. Add these paths to your Path environment variable (separate with a semicolon):
 * ```PYTHONPATH\```
 * ```PYTHONPATH\Scripts\```
 * ```RTMPDUMPPATH\``` (or specify full path with --rtmpdump option)
 * ```PLAYERPATH\``` (or specify full path with --player option)
5. From the source tree run ```python setup.py install```.
This should install any missing Python dependencies automatically.


Dependencies
------------
Livestreamer and it's plugins currently depends on these software:

* ```Python``` (CPython >= 2.6 or >= 3.0 or PyPy)
* ```python-setuptools``` or ```python-distribute```

These will be installed automatically by the setup script if they are missing:
* ```python-requests``` (version >= 1.0)
* ```python-sh``` (*nix, version >= 1.07) or ```python-pbs``` (Windows)
* ```python-argparse``` (only needed on Python version 2.6, 3.0 and 3.1)

For RTMP based plugins:
* ```librtmp/rtmpdump``` (git clone after 2011-07-31 is needed for Twitch/JustinTV plugin)


Using livestreamer API
-------------------------------

http://livestreamer.readthedocs.org/

