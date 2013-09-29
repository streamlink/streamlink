Livestreamer
============

[![PyPi Version](https://badge.fury.io/py/livestreamer.png)](http://badge.fury.io/py/livestreamer)
[![Build Status](https://secure.travis-ci.org/chrippa/livestreamer.png)](http://travis-ci.org/chrippa/livestreamer)
[![Downloads](https://pypip.in/d/livestreamer/badge.png)](https://crate.io/packages/livestreamer?version=latest)


Livestreamer is CLI program that extracts streams from various services and pipes them into
a video player of choice.

* Documentation: http://livestreamer.tanuki.se/
* GitHub: https://github.com/chrippa/livestreamer
* PyPI: https://pypi.python.org/pypi/livestreamer
* Free software: Simplified BSD license


Features
--------

Livestreamer is built upon a plugin system which allows support for new services
to be easily added. 

Currently most of the big streaming services are supported, e.g. 
[Dailymotion](http://dailymotion.com/live/),
[Livestream](http://livestream.com/),
[Twitch](http://twitch.tv/),
[Justin.tv](http://justin.tv),
[YouTube Live](http://youtube.com/live/) and [Ustream](http://ustream.tv/).


Usage
-----

The default behaviour of Livestreamer is to playback a stream in the default player (VLC).


    # pip install livestreamer
    $ livestreamer twitch.tv/day9tv best
    [cli][info] Found matching plugin justintv for URL twitch.tv/day9tv
    [cli][info] Opening stream: 720p
    [cli][info] Starting player: vlc


For more in-depth usage and install instructions see the full documentation available
at http://livestreamer.tanuki.se/.


Livestreamer related software
------------------------------

Feel free to add any Livestreamer related things to the [wiki](https://github.com/chrippa/livestreamer/wiki/).


Contributing
------------

If you wish to contribute to this project please follow these guidelines:

- Basic Git knowledge (http://gun.io/blog/how-to-github-fork-branch-and-pull-request/).
- Coding style: It's not strictly PEP8 (http://www.python.org/dev/peps/pep-0008) but at least tries to stay close to it.
- Add unit tests if possible and make sure existing ones pass.
- Make sure your code is compatible with both Python 2.6+ and 3.2+.
- Squash commits where it makes sense to do so (fixing typos or other mistakes should not be a separate commit).
- Open a pull request that relates to but one subject with a clear title and description.
- When creating a pull request, make sure it's on the correct branch. These branches are currently used:
  - master: Only critical fixes that needs to be released ASAP.
  - develop: Everything else.


