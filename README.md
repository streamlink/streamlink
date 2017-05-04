# Streamlink

[![Build Status](https://travis-ci.org/streamlink/streamlink.svg?branch=master)](https://travis-ci.org/streamlink/streamlink)
[![codecov.io](http://codecov.io/github/streamlink/streamlink/coverage.svg?branch=master)](http://codecov.io/github/streamlink/streamlink?branch=master)

Streamlink is a CLI utility that pipes flash videos from online streaming services to a variety of video players such as VLC, or alternatively, a browser.

The main purpose of streamlink is to convert CPU-heavy flash plugins to a less CPU-intensive format.

Streamlink is a fork of the [livestreamer](https://github.com/chrippa/livestreamer) project.

Please note that by using this application you're bypassing ads run by
sites such as Twitch.tv. Please consider donating or paying for subscription
services when they are available for the content you consume and enjoy.

# Installation

Streamlink can be installed by using Python or through the installers below.

**Installation via Python pip:**
```
sudo pip install streamlink
```
Note: For Windows, omit "sudo"

**Manual installation via Python:**
```
git clone https://github.com/streamlink/streamlink
sudo python setup.py install
```

**Installers for Windows/Mac/Linux:**

  - [Mac OSX](https://streamlink.github.io/install.html#other-platforms)

  - [Windows](https://streamlink.github.io/install.html#windows-binaries)

  - [Windows portable version](https://streamlink.github.io/install.html#windows-portable-version)

  - [Linux and BSD](https://streamlink.github.io/install.html#linux-and-bsd-packages)

# Features

Streamlink is built via a plugin system which allows new services to be easily added.

Major streaming services such as:
  - [Dailymotion](http://dailymotion.com/live)
  - [Livestream](https://livestream.com)
  - [Twitch](http://twitch.tv)
  - [UStream](http://ustream.tv)
  - [YouTube Live](http://youtube.com)

Are supported.

A full list of plugins can be found on the [plugin page](https://streamlink.github.io/plugin_matrix.html).


# Quickstart

After installation simply use:
```
streamlink twitch.tv/lirik source
```

And Streamlink will automatically open a default video player and begin streaming!

For full details on how to use Streamlink visit our documentation at [streamlink.github.io](https://streamlink.github.io)


# Contributing

Feel free to open a bug or contribute to code!

No need to go through a large CONTRIBUTING.md doc. The only requirement being that we get at least one ACK from a maintainer. Fork / clone us and open a PR!
