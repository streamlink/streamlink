# [Streamlink][streamlink-website]

[![Github build status][workflow-status-badge]][workflow-status]
[![codecov.io][codecov-coverage-badge]][codecov-coverage] [![Backers on Open Collective][opencollective-backers-badge]](#backers) [![Sponsors on Open Collective][opencollective-sponsors-badge]](#sponsors)

Streamlink is a CLI utility which pipes video streams from various services into a video player, such as VLC.

The main purpose of streamlink is to avoid resource-heavy and unoptimized websites, while still allowing the user to enjoy various streamed content.

Streamlink is a fork of the [Livestreamer][livestreamer] project.

Please note that by using this application you're bypassing ads run by
sites such as Twitch.tv. Please consider donating or paying for subscription
services when they are available for the content you consume and enjoy.


# [Installation][streamlink-installation]

Please refer to our documentation for different ways to install Streamlink:

- [Windows][streamlink-installation-windows]
- [macOS][streamlink-installation-macos]
- [Linux and BSD][streamlink-installation-linux-and-bsd]
- [PyPI package and source code][streamlink-installation-pypi-source]

# Features

Streamlink is built upon a plugin system which allows support for new services to be easily added.
Most of the big streaming services are supported, such as:

- [Twitch](https://www.twitch.tv)
- [YouTube](https://www.youtube.com)
- [Livestream](https://livestream.com)
- [Dailymotion](https://www.dailymotion.com)

... and many more. A full list of plugins currently included can be found on the [plugin page][streamlink-plugins].


# Quickstart

After installing, simply use:

```
streamlink STREAMURL best
```

The default behavior of Streamlink is to play back streams in the VLC player.

For more in-depth usage and install instructions, please refer to the [detailed documentation][streamlink-documentation].


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
  [streamlink-plugins]: https://streamlink.github.io/plugins.html
  [streamlink-documentation]: https://streamlink.github.io/cli.html
  [streamlink-installation]: https://streamlink.github.io/install.html
  [streamlink-installation-windows]: https://streamlink.github.io/install.html#windows
  [streamlink-installation-macos]: https://streamlink.github.io/install.html#macos
  [streamlink-installation-linux-and-bsd]: https://streamlink.github.io/install.html#linux-and-bsd
  [streamlink-installation-pypi-source]: https://streamlink.github.io/install.html#pypi-package-and-source-code
  [livestreamer]: https://github.com/chrippa/livestreamer
  [contributing]: https://github.com/streamlink/streamlink/blob/master/CONTRIBUTING.md
  [changelog]: https://github.com/streamlink/streamlink/blob/master/CHANGELOG.rst
  [contributors]: https://github.com/streamlink/streamlink/graphs/contributors
  [workflow-status]: https://github.com/streamlink/streamlink/actions?query=event%3Apush
  [workflow-status-badge]: https://github.com/streamlink/streamlink/workflows/Test,%20build%20and%20deploy/badge.svg?branch=master&event=push
  [codecov-coverage]: https://codecov.io/github/streamlink/streamlink?branch=master
  [codecov-coverage-badge]: https://codecov.io/github/streamlink/streamlink/coverage.svg?branch=master
  [opencollective-contributors]: https://opencollective.com/streamlink/contributors.svg?width=890
  [opencollective-backer]: https://opencollective.com/streamlink#backer
  [opencollective-backers]: https://opencollective.com/streamlink#backers
  [opencollective-backers-image]: https://opencollective.com/streamlink/backers.svg?width=890
  [opencollective-sponsor]: https://opencollective.com/streamlink#sponsor
  [opencollective-backers-badge]: https://opencollective.com/streamlink/backers/badge.svg
  [opencollective-sponsors-badge]: https://opencollective.com/streamlink/sponsors/badge.svg
