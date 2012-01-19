Livestreamer
============
CLI program that helps launch various streaming services in a real player instead of flash.


Installing
----------
    $ sudo python setup.py install
Livestreamer is compatible with Python version >= 2.6 and 3.0.


Using
-----
    $ livestreamer --help


Example usage
-------------
Find out what stream qualities are available

    $ livestreamer http://www.twitch.tv/ignproleague
    Found streams: 240p, 360p, 480p, 720p, iphonehigh, iphonelow, live

Now play one of them

    $ livestreamer http://www.twitch.tv/ignproleague 720p

Stream now playbacks in default player (VLC).


Saving arguments AKA config file
--------------------------------
Livestreamer can read arguments from the file ~/.livestreamerrc.
A example file:

    player=mplayer
    jtv-cookie=_jtv3_session_id=arandomhash


Notes
-----
Currently supported sites are:

* Justin.tv/Twitch.tv
* Own3D.tv
* UStream

Justin.tv plugin requires rtmpdump with jtv token support (recent git).

