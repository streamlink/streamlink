# [Streamlink][streamlink-website]

[![TravisCI build status][travisci-build-status-badge]][travisci-build-status]
[![codecov.io][codecov-coverage-badge]][codecov-coverage] [![Backers on Open Collective][opencollective-backers-badge]](#backers) [![Sponsors on Open Collective][opencollective-sponsors-badge]](#sponsors)

Streamlink is a CLI utility that pipes flash videos from online streaming services to a variety of video players such as VLC, or alternatively, a browser.

The main purpose of streamlink is to convert CPU-heavy flash plugins to a less CPU-intensive format.

Streamlink is a fork of the [Livestreamer][livestreamer] project.

Please note that by using this application you're bypassing ads run by
sites such as Twitch.tv. Please consider donating or paying for subscription
services when they are available for the content you consume and enjoy.


# [Installation][streamlink-installation]

#### Installation via Python pip

```bash
sudo pip install streamlink
```

#### Manual installation via Python

```bash
git clone https://github.com/streamlink/streamlink
sudo python setup.py install
```

#### Windows, MacOS, Linux and BSD specific installation methods

- [Windows][streamlink-installation-windows]
- [Windows portable version][streamlink-installation-windows-portable]
- [MacOS][streamlink-installation-others]
- [Linux and BSD][streamlink-installation-linux]


# Features

Streamlink is built via a plugin system which allows new services to be easily added.

Supported streaming services, among many others, are:

- [Dailymotion](https://www.dailymotion.com)
- [Livestream](https://livestream.com)
- [Twitch](https://www.twitch.tv)
- [UStream](http://www.ustream.tv)
- [YouTube Live](https://www.youtube.com)

A list of all supported plugins can be found on the [plugin page][streamlink-plugins].


# Quickstart

After installing, simply use:

```
streamlink STREAMURL best
```

Streamlink will automatically open the stream in its default video player!
See [Streamlink's detailed documentation][streamlink-documentation] for all available configuration options, CLI parameters and usage examples.


# Contributing

All contributions are welcome.
Feel free to open a new thread on the issue tracker or submit a new pull request.
Please read [CONTRIBUTING.md][contributing] first. Thanks!

[![Contributors][opencollective-contributors]][contributors]


## Backers

Thank you to all our backers! \[[Become a backer][opencollective-backer]\]

[![Backers on Open Collective][opencollective-backers-image]][opencollective-backers]


## Sponsors

Support this project by becoming a sponsor. Your logo will show up here with a link to your website. \[[Become a sponsor][opencollective-sponsor]\]

[![Open Collective Streamlink Sponsor](https://opencollective.com/streamlink/sponsor/0/avatar.svg)](https://opencollective.com/streamlink/sponsor/0/website)
[![Open Collective Streamlink Sponsor](https://opencollective.com/streamlink/sponsor/1/avatar.svg)](https://opencollective.com/streamlink/sponsor/1/website)
[![Open Collective Streamlink Sponsor](https://opencollective.com/streamlink/sponsor/2/avatar.svg)](https://opencollective.com/streamlink/sponsor/2/website)
[![Open Collective Streamlink Sponsor](https://opencollective.com/streamlink/sponsor/3/avatar.svg)](https://opencollective.com/streamlink/sponsor/3/website)
[![Open Collective Streamlink Sponsor](https://opencollective.com/streamlink/sponsor/4/avatar.svg)](https://opencollective.com/streamlink/sponsor/4/website)
[![Open Collective Streamlink Sponsor](https://opencollective.com/streamlink/sponsor/5/avatar.svg)](https://opencollective.com/streamlink/sponsor/5/website)
[![Open Collective Streamlink Sponsor](https://opencollective.com/streamlink/sponsor/6/avatar.svg)](https://opencollective.com/streamlink/sponsor/6/website)
[![Open Collective Streamlink Sponsor](https://opencollective.com/streamlink/sponsor/7/avatar.svg)](https://opencollective.com/streamlink/sponsor/7/website)
[![Open Collective Streamlink Sponsor](https://opencollective.com/streamlink/sponsor/8/avatar.svg)](https://opencollective.com/streamlink/sponsor/8/website)
[![Open Collective Streamlink Sponsor](https://opencollective.com/streamlink/sponsor/9/avatar.svg)](https://opencollective.com/streamlink/sponsor/9/website)


  [streamlink-website]: https://streamlink.github.io
  [streamlink-plugins]: https://streamlink.github.io/plugin_matrix.html
  [streamlink-documentation]: https://streamlink.github.io/cli.html
  [streamlink-installation]: https://streamlink.github.io/install.html
  [streamlink-installation-windows]: https://streamlink.github.io/install.html#windows-binaries
  [streamlink-installation-windows-portable]: https://streamlink.github.io/install.html#windows-portable-version
  [streamlink-installation-linux]: https://streamlink.github.io/install.html#linux-and-bsd-packages
  [streamlink-installation-others]: https://streamlink.github.io/install.html#other-platforms
  [livestreamer]: https://github.com/chrippa/livestreamer
  [contributing]: https://github.com/streamlink/streamlink/blob/master/CONTRIBUTING.md
  [changelog]: https://github.com/streamlink/streamlink/blob/master/CHANGELOG.rst
  [contributors]: https://github.com/streamlink/streamlink/graphs/contributors
  [travisci-build-status]: https://travis-ci.org/streamlink/streamlink
  [travisci-build-status-badge]: https://travis-ci.org/streamlink/streamlink.svg?branch=master
  [codecov-coverage]: https://codecov.io/github/streamlink/streamlink?branch=master
  [codecov-coverage-badge]: https://codecov.io/github/streamlink/streamlink/coverage.svg?branch=master
  [opencollective-contributors]: https://opencollective.com/streamlink/contributors.svg?width=890
  [opencollective-backer]: https://opencollective.com/streamlink#backer
  [opencollective-backers]: https://opencollective.com/streamlink#backers
  [opencollective-backers-image]: https://opencollective.com/streamlink/backers.svg?width=890
  [opencollective-sponsor]: https://opencollective.com/streamlink#sponsor
  [opencollective-backers-badge]: https://opencollective.com/streamlink/backers/badge.svg
  [opencollective-sponsors-badge]: https://opencollective.com/streamlink/sponsors/badge.svg
