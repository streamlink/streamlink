# Streamlink

Streamlink is a CLI utility that pipes flash videos from online streaming services to a variety of video players such as VLC, or alternatively, a browser.

The main purpose of streamlink is to convert CPU-heavy flash plugins to a less CPU-intensive format.

Streamlink is a fork of the [livestreamer](https://github.com/chrippa/livestreamer) project.

# Features

Streamlink is built via a plugin system which allows new services to be easily added.

Major streaming services such as:
  - [Dailymotion](http://dailymotion.com/live)
  - [Livestream](https://livestream.com)
  - [Twitch](http://twitch.tv)
  - [UStream](http://ustream.tv)
  - [YouTube Live](http://youtube.com)

Are supported.

A full list of plugins can be found in the plugin directory:

```
src/streamlink/plugins
▶ ls
afreeca.py        common_jwplayer.py  drdk.py        letontv.py        periscope.py               tga.py         viasat_embed.py
afreecatv.py      common_swf.py       euronews.py    livestation.py    picarto.py                 tv3cat.py      viasat.py
aftonbladet.py    connectcast.py      filmon.py      livestream.py     rtve.py                    tv4play.py     wattv.py
alieztv.py        crunchyroll.py      filmon_us.py   media_ccc_de.py   sbsdiscovery.py            tvcatchup.py   weeb.py
ard_live.py       cybergame.py        furstream.py   mips.py           seemeplay.py               tvplayer.py    youtube.py
ard_mediathek.py  dailymotion.py      gaminglive.py  mlgtv.py          speedrunslive.py           twitch.py      zdf_mediathek.py
artetv.py         disney_de.py        gomexp.py      nhkworld.py       ssh101.py                  ustreamtv.py
azubutv.py        dmcloud_embed.py    goodgame.py    nos.py            streamingvideoprovider.py  vaughnlive.py
bambuser.py       dmcloud.py          hitbox.py      npo.py            streamlive.py              veetle.py
beattv.py         dommune.py          __init__.py    nrk.py            stream.py                  vgtv.py
chaturbate.py     douyutv.py          itvplayer.py   oldlivestream.py  svtplay.py                 viagame.py
```

# Quickstart

We've only just recently forked, but please be patient while we update the code :) (September 17, 2016)

# Contributing

Feel free to open a bug or contribute to code!

No need to go through a large CONTRIBUTING.md doc. The only requirement being that we get at least one ACK from a maintainer. Fork / clone us and open a PR!
