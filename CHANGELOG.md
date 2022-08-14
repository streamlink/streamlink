# Changelog

## streamlink 4.3.0 (2022-08-15)

Release highlights:

- Improved: CLI download progress output ([#4656](https://github.com/streamlink/streamlink/pull/4656))
- Fixed: consecutive FFmpeg executable lookups not being cached ([#4660](https://github.com/streamlink/streamlink/pull/4660))
- Fixed: `--ffmpeg-verbose-path` not expanding `~` to the user's home directory ([#4688](https://github.com/streamlink/streamlink/pull/4688))
- Fixed: deprecated stdlib API calls in the upcoming Python 3.11 release ([#4651](https://github.com/streamlink/streamlink/pull/4651), [#4654](https://github.com/streamlink/streamlink/pull/4654))
- Fixed: huya plugin ([#4685](https://github.com/streamlink/streamlink/pull/4685))
- Fixed: livestream plugin ([#4679](https://github.com/streamlink/streamlink/pull/4679))
- Fixed: picarto plugin ([#4729](https://github.com/streamlink/streamlink/pull/4729))
- Fixed: nbcnews plugin ([#4668](https://github.com/streamlink/streamlink/pull/4668))
- Fixed: deutschewelle plugin ([#4725](https://github.com/streamlink/streamlink/pull/4725))
- Added plugins: atpchallenger ([#4700](https://github.com/streamlink/streamlink/pull/4700))
- Removed plugins: nbc + nbcsports + theplatform ([#4731](https://github.com/streamlink/streamlink/pull/4731)), common\_jwplayer ([#4733](https://github.com/streamlink/streamlink/pull/4733))
- Docs: various CLI related improvements ([#4659](https://github.com/streamlink/streamlink/pull/4659))
- Docs: removed OpenBSD and Ubuntu from install docs ([#4681](https://github.com/streamlink/streamlink/pull/4681))
- Plugin API: added new validation schemas and updated validators ([#4691](https://github.com/streamlink/streamlink/pull/4691), [#4709](https://github.com/streamlink/streamlink/pull/4709), [#4732](https://github.com/streamlink/streamlink/pull/4732))

[Full changelog](https://github.com/streamlink/streamlink/compare/4.2.0...4.3.0)


## streamlink 4.2.0 (2022-07-09)

Release highlights:

- Added: new Windows portable builds ([#4581](https://github.com/streamlink/streamlink/pull/4581))
- Added: more dependency versions to debug log header ([#4575](https://github.com/streamlink/streamlink/pull/4575))
- Added: parsed multivariant playlist reference to `HLSStream` and `MuxedHLSStream` ([#4568](https://github.com/streamlink/streamlink/pull/4568))
- Fixed: unnecessary delay when closing `DASHStream`s ([#4630](https://github.com/streamlink/streamlink/pull/4630))
- Fixed: `FFmpegMuxer` not closing sub-streams concurrently ([#4634](https://github.com/streamlink/streamlink/pull/4634))
- Fixed: threading issue when closing `WebsocketClient` connections ([#4608](https://github.com/streamlink/streamlink/pull/4608))
- Fixed: handling of `PluginError`s when outputting JSON data via `--json` ([#4590](https://github.com/streamlink/streamlink/pull/4590))
- Fixed: broken YouTube plugin when setting custom authentication headers ([#4576](https://github.com/streamlink/streamlink/pull/4576))
- Fixed: "source" Twitch VODs not being considered "best" ([#4625](https://github.com/streamlink/streamlink/pull/4625))
- Fixed: and rewritten FilmOn plugin ([#4573](https://github.com/streamlink/streamlink/pull/4573))
- Fixed: websocket issue in Twitcasting plugin ([#4608](https://github.com/streamlink/streamlink/pull/4608), [#4628](https://github.com/streamlink/streamlink/pull/4628))
- Fixed: VK plugin ([#4613](https://github.com/streamlink/streamlink/pull/4613), [#4638](https://github.com/streamlink/streamlink/pull/4638))
- Fixed: various other plugin issues (see full changelog)
- New plugins: Aloula ([#4572](https://github.com/streamlink/streamlink/pull/4572))
- Removed plugins: Eltrecetv ([#4593](https://github.com/streamlink/streamlink/pull/4593))
- Docs: added openSUSE ([#4596](https://github.com/streamlink/streamlink/pull/4596)) and Scoop ([#4600](https://github.com/streamlink/streamlink/pull/4600)) packages
- Docs: improved some links in CLI docs ([#4623](https://github.com/streamlink/streamlink/pull/4623))
- Docs: upgraded `furo` theme to `2022.06.04.1`, require `sphinx` `>=4`, and replace `recommonmark` with `myst-parser` ([#4610](https://github.com/streamlink/streamlink/pull/4610))
- Build: fixed outdated `python_requires` value in `setup.cfg` ([#4580](https://github.com/streamlink/streamlink/pull/4580))
- Build: upgraded `versioningit` build dependency to `>=2.0.0 <3` ([#4597](https://github.com/streamlink/streamlink/pull/4597))

[Full changelog](https://github.com/streamlink/streamlink/compare/4.1.0...4.2.0)


## streamlink 4.1.0 (2022-05-30)

Release highlights:

- Improved: decryption of HLS streams ([#4533](https://github.com/streamlink/streamlink/pull/4533))
- Improved: HLS playlist parsing ([#4540](https://github.com/streamlink/streamlink/pull/4540), [#4552](https://github.com/streamlink/streamlink/pull/4552))
- Improved: validation schemas and error handling/printing ([#4514](https://github.com/streamlink/streamlink/pull/4514))
- Improved: string representations of `Stream` implementations ([#4521](https://github.com/streamlink/streamlink/pull/4521))
- Fixed: new YouTube consent dialog ([#4515](https://github.com/streamlink/streamlink/pull/4515))
- Fixed: crunchyroll plugin ([#4510](https://github.com/streamlink/streamlink/pull/4510))
- Fixed: nicolive email logins ([#4553](https://github.com/streamlink/streamlink/pull/4553))
- Fixed: threading issue when closing segmented streams ([#4517](https://github.com/streamlink/streamlink/pull/4517))
- Removed: suppression of `InsecureRequestWarning` ([#4525](https://github.com/streamlink/streamlink/pull/4525))
- New plugins: blazetv ([#4548](https://github.com/streamlink/streamlink/pull/4548)), hiplayer ([#4507](https://github.com/streamlink/streamlink/pull/4507)), useetv ([#4536](https://github.com/streamlink/streamlink/pull/4536))
- Removed plugins: rotana ([#4512](https://github.com/streamlink/streamlink/pull/4512))

[Full changelog](https://github.com/streamlink/streamlink/compare/4.0.1...4.1.0)


## streamlink 4.0.1 (2022-05-01)

No code changes.  
Please see the [changelog of the `4.0.0` release](https://streamlink.github.io/changelog.html#streamlink-4-0-0-2022-05-01), as it contains breaking changes.

- Fixed: missing source-dist tarballs on GitHub release page ([#4503](https://github.com/streamlink/streamlink/pull/4503))

[Full changelog](https://github.com/streamlink/streamlink/compare/4.0.0...4.0.1)


## streamlink 4.0.0 (2022-05-01)

Breaking changes:

- BREAKING: dropped support for Python 3.6 ([#4442](https://github.com/streamlink/streamlink/pull/4442))
- BREAKING/API: removed [`streamlink.plugin.api.utils`](https://streamlink.github.io/deprecations.html#removal-of-streamlink-plugin-api-utils) module ([#4467](https://github.com/streamlink/streamlink/pull/4467))
- BREAKING/setup: switched to PEP 518 build system declaration and replaced versioneer in favor of versioningit ([#4440](https://github.com/streamlink/streamlink/pull/4440))
- BREAKING/packaging: replaced Windows installers with new ones built at [streamlink/windows-installer](https://github.com/streamlink/windows-installer) ([#4405](https://github.com/streamlink/streamlink/pull/4405))
  - Added: new embedded Python builds for 3.8 and 3.10, both x86 and x86_64
  - Updated: embedded FFmpeg to 5.0

Release highlights:

- Added: support for `--record=-`, for writing data to stdout while watching at the same time ([#4462](https://github.com/streamlink/streamlink/pull/4462))
- Added: `plugin` variable for `--title`, `--output`, `--record` and `--record-and-pipe` ([#4437](https://github.com/streamlink/streamlink/pull/4437))
- Added: missing CLI protocol parameter support for DASH streams ([#4434](https://github.com/streamlink/streamlink/pull/4434))
- Updated: CLI and API documentation ([#4415](https://github.com/streamlink/streamlink/pull/4415), [#4424](https://github.com/streamlink/streamlink/pull/4424), [#4430](https://github.com/streamlink/streamlink/pull/4430))
- Updated: plugin description documentation ([#4391](https://github.com/streamlink/streamlink/pull/4391))
- Fixed: nicolive email logins ([#4380](https://github.com/streamlink/streamlink/pull/4380))
- Fixed: various other plugin issues (see the changelog down below)
- New plugins: cmmedia ([#4416](https://github.com/streamlink/streamlink/pull/4416)), htv ([#4431](https://github.com/streamlink/streamlink/pull/4431)), mdstrm ([#4395](https://github.com/streamlink/streamlink/pull/4395)), trovo ([#4471](https://github.com/streamlink/streamlink/pull/4471))
- Removed plugins: abweb ([#4270](https://github.com/streamlink/streamlink/pull/4270)), garena ([#4460](https://github.com/streamlink/streamlink/pull/4460)), senategov ([#4458](https://github.com/streamlink/streamlink/pull/4458)), teamliquid ([#4393](https://github.com/streamlink/streamlink/pull/4393)), tlctr ([#4432](https://github.com/streamlink/streamlink/pull/4432)), vrtbe ([#4459](https://github.com/streamlink/streamlink/pull/4459))

[Full changelog](https://github.com/streamlink/streamlink/compare/3.2.0...4.0.0)


## streamlink 3.2.0 (2022-03-05)

Release highlights:

- Added: log message for the resolved path when writing output to file ([#4336](https://github.com/streamlink/streamlink/pull/4336))
- Added: new plugins for rtpa.es ([#4344](https://github.com/streamlink/streamlink/pull/4344)) and lnk.lt ([#4364](https://github.com/streamlink/streamlink/pull/4364))
- Changed: metadata requirements for built-in plugins ([#4374](https://github.com/streamlink/streamlink/pull/4374))
- Improved: plugins documentation ([#4374](https://github.com/streamlink/streamlink/pull/4374))
- Fixed: filmon plugin, requires at least OpenSSL 1.1.0 ([#4335](https://github.com/streamlink/streamlink/pull/4335), [#4345](https://github.com/streamlink/streamlink/pull/4345))
- Fixed: mildom plugin ([#4375](https://github.com/streamlink/streamlink/pull/4375))
- Fixed: nicolive email logins with confirmation codes ([#4380](https://github.com/streamlink/streamlink/pull/4380))
- Fixed: various other plugin issues, see the changelog down below
- Upgraded: Windows installer's Python and dependency versions ([#4330](https://github.com/streamlink/streamlink/pull/4330), [#4347](https://github.com/streamlink/streamlink/pull/4347))

[Full changelog](https://github.com/streamlink/streamlink/compare/3.1.1...3.2.0)


## streamlink 3.1.1 (2022-01-25)

Patch release:

- Fixed: broken `streamlink.exe`/`streamlinkw.exe` executables in Windows installer ([#4308](https://github.com/streamlink/streamlink/pull/4308))

[Full changelog](https://github.com/streamlink/streamlink/compare/3.1.0...3.1.1)


## streamlink 3.1.0 (2022-01-22)

Release highlights:

- Changed: file overwrite prompt to wait for user input before opening streams ([#4252](https://github.com/streamlink/streamlink/pull/4252))
- Fixed: log messages appearing in `--json` output ([#4258](https://github.com/streamlink/streamlink/pull/4258))
- Fixed: keep-alive TCP connections when filtering out HLS segments ([#4229](https://github.com/streamlink/streamlink/pull/4229))
- Fixed: sort order of DASH streams with the same video resolution ([#4220](https://github.com/streamlink/streamlink/pull/4220))
- Fixed: HLS segment byterange offsets ([#4301](https://github.com/streamlink/streamlink/pull/4301), [#4302](https://github.com/streamlink/streamlink/pull/4302))
- Fixed: YouTube /live URLs ([#4222](https://github.com/streamlink/streamlink/pull/4222))
- Fixed: UStream websocket address ([#4238](https://github.com/streamlink/streamlink/pull/4238))
- Fixed: Pluto desync issues by filtering out bumper segments ([#4255](https://github.com/streamlink/streamlink/pull/4255))
- Fixed: various plugin issues - please see the changelog down below
- Removed plugins: abweb ([#4270](https://github.com/streamlink/streamlink/pull/4270)), latina ([#4269](https://github.com/streamlink/streamlink/pull/4269)), live_russia_tv ([#4263](https://github.com/streamlink/streamlink/pull/4263)), liveme ([#4264](https://github.com/streamlink/streamlink/pull/4264))

[Full changelog](https://github.com/streamlink/streamlink/compare/3.0.3...3.1.0)


## streamlink 3.0.3 (2021-11-27)

Patch release:

- Fixed: broken output of the `--help` CLI argument ([#4213](https://github.com/streamlink/streamlink/pull/4213))
- Fixed: parsing of invalid HTML5 documents ([#4210](https://github.com/streamlink/streamlink/pull/4210))

Please see the [changelog of 3.0.0](https://streamlink.github.io/changelog.html#streamlink-3-0-0-2021-11-17), as it contains breaking changes that may require user interaction.

[Full changelog](https://github.com/streamlink/streamlink/compare/3.0.2...3.0.3)


## streamlink 3.0.2 (2021-11-25)

Patch release:

- Added: support for the `id` plugin metadata property ([#4203](https://github.com/streamlink/streamlink/pull/4203))
- Updated: Twitch access token request parameter regarding embedded ads ([#4194](https://github.com/streamlink/streamlink/pull/4194))
- Fixed: early `SIGINT`/`SIGTERM` signal handling ([#4190](https://github.com/streamlink/streamlink/pull/4190))
- Fixed: broken character set decoding when parsing HTML documents ([#4201](https://github.com/streamlink/streamlink/pull/4201))
- Fixed: missing home directory expansion (tilde character) in file output paths ([#4204](https://github.com/streamlink/streamlink/pull/4204))
- New plugin: tviplayer ([#4199](https://github.com/streamlink/streamlink/pull/4199))

[Full changelog](https://github.com/streamlink/streamlink/compare/3.0.1...3.0.2)


## streamlink 3.0.1 (2021-11-17)

Patch release:

- Fixed: broken pycountry import in Windows installer's Python environment ([#4180](https://github.com/streamlink/streamlink/pull/4180))

[Full changelog](https://github.com/streamlink/streamlink/compare/3.0.0...3.0.1)


## streamlink 3.0.0 (2021-11-17)

Breaking changes:

- BREAKING: dropped support for RTMP, HDS and AkamaiHD streams ([#4169](https://github.com/streamlink/streamlink/pull/4169), [#4168](https://github.com/streamlink/streamlink/pull/4168))
  - removed the `rtmp://`, `hds://` and `akamaihd://` protocol plugins
  - removed all Flash related code
  - upgraded all plugins using these old streaming protocols
  - dropped RTMPDump dependency
- BREAKING: removed the following CLI arguments (and respective session options): ([#4169](https://github.com/streamlink/streamlink/pull/4169), [#4168](https://github.com/streamlink/streamlink/pull/4168))
  - `--rtmp-rtmpdump`, `--rtmpdump`, `--rtmp-proxy`, `--rtmp-timeout`  
    Users of Streamlink's Windows installer will need to update their [config file](https://streamlink.github.io/cli.html#configuration-file).
  - `--subprocess-cmdline`, `--subprocess-errorlog`, `--subprocess-errorlog-path`
  - `--hds-live-edge`, `--hds-segment-attempts`, `--hds-segment-threads`, `--hds-segment-timeout`, `--hds-timeout`
- BREAKING: switched from HTTP to HTTPS for all kinds of scheme-less input URLs. If a site or http-proxy doesn't support HTTPS, then HTTP needs to be set explicitly. ([#4068](https://github.com/streamlink/streamlink/pull/4068), [#4053](https://github.com/streamlink/streamlink/pull/4053))
- BREAKING/API: changed `Session.resolve_url()` and `Session.resolve_url_no_redirect()` to return a tuple of a plugin class and the resolved URL instead of an initialized plugin class instance. This fixes the availability of plugin options in a plugin's constructor. ([#4163](https://github.com/streamlink/streamlink/pull/4163))
- BREAKING/requirements: dropped alternative dependency `pycrypto` and removed the `STREAMLINK_USE_PYCRYPTO` env var switch ([#4174](https://github.com/streamlink/streamlink/pull/4174))
- BREAKING/requirements: switched from `iso-639`+`iso3166` to `pycountry` and removed the `STREAMLINK_USE_PYCOUNTRY` env var switch ([#4175](https://github.com/streamlink/streamlink/pull/4175))
- BREAKING/setup: disabled unsupported Python versions, disabled the deprecated `test` setuptools command, removed the `NO_DEPS` env var, and switched to declarative package data via `setup.cfg` ([#4079](https://github.com/streamlink/streamlink/pull/4079), [#4107](https://github.com/streamlink/streamlink/pull/4107), [#4115](https://github.com/streamlink/streamlink/pull/4115), [#4113](https://github.com/streamlink/streamlink/pull/4113))

Release highlights:

- Deprecated: `--https-proxy` in favor of a single `--http-proxy` CLI argument (and respective session option). Both now set the same proxy for all HTTPS/HTTP requests and websocket connections. [`--https-proxy` will be removed in a future release.](https://streamlink.github.io/deprecations.html#streamlink-3-0-0) ([#4120](https://github.com/streamlink/streamlink/pull/4120))
- Added: official support for Python 3.10 ([#4144](https://github.com/streamlink/streamlink/pull/4144))
- Added: `--twitch-api-header` for only setting Twitch.tv API requests headers (for authentication, etc.) as an alternative to `--http-header` ([#4156](https://github.com/streamlink/streamlink/pull/4156))
- Added: BASH and ZSH completions to sdist tarball and wheels. ([#4048](https://github.com/streamlink/streamlink/pull/4048), [#4178](https://github.com/streamlink/streamlink/pull/4178))
- Added: support for creating parent directories via metadata variables in file output paths ([#4085](https://github.com/streamlink/streamlink/pull/4085))
- Added: new WebsocketClient implementation ([#4153](https://github.com/streamlink/streamlink/pull/4153))
- Updated: plugins using websocket connections - nicolive, ustreamtv, twitcasting ([#4155](https://github.com/streamlink/streamlink/pull/4155), [#4164](https://github.com/streamlink/streamlink/pull/4164), [#4154](https://github.com/streamlink/streamlink/pull/4154))
- Updated: circumvention for YouTube's age verification ([#4058](https://github.com/streamlink/streamlink/pull/4058))
- Updated: and fixed lots of other plugins, see the detailed changelog below
- Reverted: HLS segment downloads always being streamed, and added back `--hls-segment-stream-data` to prevent connection issues ([#4159](https://github.com/streamlink/streamlink/pull/4159))
- Fixed: URL percent-encoding for sites which require the lowercase format ([#4003](https://github.com/streamlink/streamlink/pull/4003))
- Fixed: XML parsing issues ([#4075](https://github.com/streamlink/streamlink/pull/4075))
- Fixed: broken `method` parameter when using the `httpstream://` protocol plugin ([#4171](https://github.com/streamlink/streamlink/pull/4171))
- Fixed: test failures when the `brotli` package is installed ([#4022](https://github.com/streamlink/streamlink/pull/4022))
- Requirements: bumped `lxml` to `>4.6.4,<5.0` and `websocket-client` to `>=1.2.1,<2.0` ([#4143](https://github.com/streamlink/streamlink/pull/4143), [#4153](https://github.com/streamlink/streamlink/pull/4153))
- Windows installer: upgraded Python to `3.9.8` and FFmpeg to `n4.4.1` ([#4176](https://github.com/streamlink/streamlink/pull/4176), [#4124](https://github.com/streamlink/streamlink/pull/4124))
- Documentation: upgraded to first stable version of the Furo theme ([#4000](https://github.com/streamlink/streamlink/pull/4000))
- New plugins: pandalive ([#4064](https://github.com/streamlink/streamlink/pull/4064))
- Removed plugins: tga ([#4129](https://github.com/streamlink/streamlink/pull/4129)), viasat ([#4087](https://github.com/streamlink/streamlink/pull/4087)), viutv ([#4018](https://github.com/streamlink/streamlink/pull/4018)), webcast_india_gov ([#4024](https://github.com/streamlink/streamlink/pull/4024))

[Full changelog](https://github.com/streamlink/streamlink/compare/2.4.0...3.0.0)


## streamlink 2.4.0 (2021-09-07)

Release highlights:

- Deprecated: stream-type specific stream transport options in favor of generic options ([#3893](https://github.com/streamlink/streamlink/pull/3893))
  - use `--stream-segment-attempts` instead of `--{dash,hds,hls}-segment-attempts`
  - use `--stream-segment-threads` instead of `--{dash,hds,hls}-segment-threads`
  - use `--stream-segment-timeout` instead of `--{dash,hds,hls}-segment-timeout`
  - use `--stream-timeout` instead of `--{dash,hds,hls,rtmp,http-stream}-timeout`

  See the documentation's [deprecations page](https://streamlink.github.io/latest/deprecations.html#streamlink-2-4-0) for more information.
- Deprecated: `--hls-segment-stream-data` option and made it always stream segment data ([#3894](https://github.com/streamlink/streamlink/pull/3894))
- Updated: Python version of the Windows installer from 3.8 to 3.9 and dropped support for Windows 7 due to Python incompatibilities ([#3918](https://github.com/streamlink/streamlink/pull/3918))  
  See the documentation's [install page](https://streamlink.github.io/install.html) for alternative installation methods on Windows 7.
- Updated: FFmpeg in the Windows Installer from 4.2 (Zeranoe) to 4.4 ([streamlink/FFmpeg-Builds](https://github.com/streamlink/FFmpeg-Builds)) ([#3981](https://github.com/streamlink/streamlink/pull/3981))
- Added: `{author}`, `{category}`/`{game}`, `{title}` and `{url}` variables to `--output`, `--record` and `--record-and-play` ([#3962](https://github.com/streamlink/streamlink/pull/3962))
- Added: `{time}`/`{time:custom-format}` variable to `--title`, `--output`, `--record` and `--record-and-play` ([#3993](https://github.com/streamlink/streamlink/pull/3993))
- Added: `--fs-safe-rules` for changing character replacement rules in file outputs ([#3962](https://github.com/streamlink/streamlink/pull/3962))
- Added: plugin metadata to `--json` stream data output ([#3987](https://github.com/streamlink/streamlink/pull/3987))
- Fixed: named pipes not being cleaned up by FFMPEGMuxer ([#3992](https://github.com/streamlink/streamlink/pull/3992))
- Fixed: KeyError on invalid variables in `--player-args` ([#3988](https://github.com/streamlink/streamlink/pull/3988))
- Fixed: tests failing in certain cases when run in different order ([#3920](https://github.com/streamlink/streamlink/pull/3920))
- Fixed: initial HLS playlist parsing issues ([#3903](https://github.com/streamlink/streamlink/pull/3903), [#3910](https://github.com/streamlink/streamlink/pull/3910))
- Fixed: various plugin issues. Please see the changelog down below.
- Dependencies: added `lxml>=4.6.3` ([#3952](https://github.com/streamlink/streamlink/pull/3952))
- Dependencies: switched back to `requests>=2.26.0` on Windows ([#3930](https://github.com/streamlink/streamlink/pull/3930))
- Removed plugins: animeworld ([#3951](https://github.com/streamlink/streamlink/pull/3951)), gardenersworld ([#3966](https://github.com/streamlink/streamlink/pull/3966)), huomao ([#3932](https://github.com/streamlink/streamlink/pull/3932))

[Full changelog](https://github.com/streamlink/streamlink/compare/2.3.0...2.4.0)


## streamlink 2.3.0 (2021-07-26)

Release highlights:

- Implemented: new plugin URL matching API ([#3814](https://github.com/streamlink/streamlink/issues/3814), [#3821](https://github.com/streamlink/streamlink/pull/3821))  
  Third-party plugins which use the old API will still be resolved, but those plugins will have to upgrade in the future. See the documentation's [deprecations page](https://streamlink.github.io/latest/deprecations.html#streamlink-2-3-0) for more information.
- Implemented: HLS media initialization section (fragmented MPEG-4 streams) ([#3828](https://github.com/streamlink/streamlink/pull/3828))
- Upgraded: `requests` to `>=2.26.0,<3` and set it to `==2.25.1` on Windows ([#3864](https://github.com/streamlink/streamlink/pull/3864), [#3880](https://github.com/streamlink/streamlink/pull/3880))
- Fixed: YouTube channel URLs, premiering live streams, added API fallback ([#3847](https://github.com/streamlink/streamlink/pull/3847), [#3873](https://github.com/streamlink/streamlink/pull/3873), [#3809](https://github.com/streamlink/streamlink/pull/3809))
- Removed plugins: canalplus ([#3841](https://github.com/streamlink/streamlink/pull/3841)), dommune ([#3818](https://github.com/streamlink/streamlink/pull/3818)), liveedu ([#3845](https://github.com/streamlink/streamlink/pull/3845)), periscope ([#3813](https://github.com/streamlink/streamlink/pull/3813)), powerapp ([#3816](https://github.com/streamlink/streamlink/pull/3816)), rtlxl ([#3842](https://github.com/streamlink/streamlink/pull/3842)), streamingvideoprovider ([#3843](https://github.com/streamlink/streamlink/pull/3843)), teleclubzoom ([#3817](https://github.com/streamlink/streamlink/pull/3817)), tigerdile ([#3819](https://github.com/streamlink/streamlink/pull/3819))

[Full changelog](https://github.com/streamlink/streamlink/compare/2.2.0...2.3.0)


## streamlink 2.2.0 (2021-06-19)

Release highlights:

- Changed: default config file path on macOS and Windows ([#3766](https://github.com/streamlink/streamlink/pull/3766))  
  - macOS: `${HOME}/Library/Application Support/streamlink/config`
  - Windows: `%APPDATA%\streamlink\config`
- Changed: default custom plugins directory path on macOS and Linux/BSD ([#3766](https://github.com/streamlink/streamlink/pull/3766))
  - macOS: `${HOME}/Library/Application Support/streamlink/plugins`
  - Linux/BSD: `${XDG_DATA_HOME:-${HOME}/.local/share}/streamlink/plugins`
- Deprecated: old config file paths and old custom plugins directory paths ([#3784](https://github.com/streamlink/streamlink/pull/3784))
  - Windows:
    - `%APPDATA%\streamlink\streamlinkrc`
  - macOS:
    - `${XDG_CONFIG_HOME:-${HOME}/.config}/streamlink/config`
    - `${XDG_CONFIG_HOME:-${HOME}/.config}/streamlink/plugins`
    - `${HOME}/.streamlinkrc`
  - Linux/BSD:
    - `${XDG_CONFIG_HOME:-${HOME}/.config}/streamlink/plugins`
    - `${HOME}/.streamlinkrc`

  Support for these old paths will be dropped in the future.  
  See the [CLI documentation](https://streamlink.github.io/cli.html) for all the details regarding these changes.
- Implemented: `--logfile` CLI argument ([#3753](https://github.com/streamlink/streamlink/pull/3753))
- Fixed: Youtube 404 errors by dropping private API calls (plugin rewrite) ([#3797](https://github.com/streamlink/streamlink/pull/3797))
- Fixed: Twitch clips ([#3762](https://github.com/streamlink/streamlink/pull/3762), [#3775](https://github.com/streamlink/streamlink/pull/3775)) and hosted channel redirection ([#3776](https://github.com/streamlink/streamlink/pull/3776))
- Fixed: Olympicchannel plugin ([#3760](https://github.com/streamlink/streamlink/pull/3760))
- Fixed: various Zattoo plugin issues ([#3773](https://github.com/streamlink/streamlink/pull/3773), [#3780](https://github.com/streamlink/streamlink/pull/3780))
- Fixed: HTTP responses with truncated body and mismatching content-length header ([#3768](https://github.com/streamlink/streamlink/pull/3768))
- Fixed: scheme-less URLs with address:port for `--http-proxy`, etc. ([#3765](https://github.com/streamlink/streamlink/pull/3765))
- Fixed: rendered man page path on Sphinx 4 ([#3750](https://github.com/streamlink/streamlink/pull/3750))
- Added plugins: mildom.com ([#3584](https://github.com/streamlink/streamlink/pull/3584)), booyah.live ([#3585](https://github.com/streamlink/streamlink/pull/3585)), mediavitrina.ru ([#3743](https://github.com/streamlink/streamlink/pull/3743))
- Removed plugins: ine.com ([#3781](https://github.com/streamlink/streamlink/pull/3781)), playtv.fr ([#3798](https://github.com/streamlink/streamlink/pull/3798))

[Full changelog](https://github.com/streamlink/streamlink/compare/2.1.2...2.2.0)


## streamlink 2.1.2 (2021-05-20)

Patch release:

- Fixed: youtube 404 errors ([#3732](https://github.com/streamlink/streamlink/pull/3732)), consent dialog ([#3672](https://github.com/streamlink/streamlink/pull/3672)) and added short URLs ([#3677](https://github.com/streamlink/streamlink/pull/3677))
- Fixed: picarto plugin ([#3661](https://github.com/streamlink/streamlink/pull/3661))
- Fixed: euronews plugin ([#3698](https://github.com/streamlink/streamlink/pull/3698))
- Fixed: bbciplayer plugin ([#3725](https://github.com/streamlink/streamlink/pull/3725))
- Fixed: missing removed-plugins-file in `setup.py build` ([#3653](https://github.com/streamlink/streamlink/pull/3653))
- Changed: HLS streams to use rounded bandwidth names ([#3721](https://github.com/streamlink/streamlink/pull/3721))
- Removed: plugin for hitbox.tv / smashcast.tv ([#3686](https://github.com/streamlink/streamlink/pull/3686)), tvplayer.com ([#3673](https://github.com/streamlink/streamlink/pull/3673))

[Full changelog](https://github.com/streamlink/streamlink/compare/2.1.1...2.1.2)


## streamlink 2.1.1 (2021-03-25)

Patch release:

- Fixed: test failure due to missing removed plugins file in sdist tarball ([#3644](https://github.com/streamlink/streamlink/pull/3644)).

[Full changelog](https://github.com/streamlink/streamlink/compare/2.1.0...2.1.1)


## streamlink 2.1.0 (2021-03-22)

Release highlights:

- Added: `--interface`, `-4` / `--ipv4` and `-6` / `--ipv6` ([#3483](https://github.com/streamlink/streamlink/pull/3483))
- Added: `--niconico-purge-credentials` ([#3434](https://github.com/streamlink/streamlink/pull/3434))
- Added: `--twitcasting-password` ([#3505](https://github.com/streamlink/streamlink/pull/3505))
- Added: Linux AppImages ([#3611](https://github.com/streamlink/streamlink/pull/3611))
- Added: pre-built man page to bdist wheels and sdist tarballs ([#3459](https://github.com/streamlink/streamlink/pull/3459), [#3510](https://github.com/streamlink/streamlink/pull/3510))
- Added: plugin for ahaber.com.tr and atv.com.tr ([#3484](https://github.com/streamlink/streamlink/pull/3484)), nimo.tv ([#3508](https://github.com/streamlink/streamlink/pull/3508))
- Fixed: `--player-http` / `--player-continuous-http` HTTP server being bound to all interfaces ([#3450](https://github.com/streamlink/streamlink/pull/3450))
- Fixed: handling of languages without alpha_2 code when using pycountry ([#3518](https://github.com/streamlink/streamlink/pull/3518))
- Fixed: memory leak when calling `streamlink.streams()` ([#3486](https://github.com/streamlink/streamlink/pull/3486))
- Fixed: race condition in HLS related tests ([#3454](https://github.com/streamlink/streamlink/pull/3454))
- Fixed: `--player-fifo` issues on Windows with VLC or MPV ([#3619](https://github.com/streamlink/streamlink/pull/3619))
- Fixed: various plugins issues (see detailed changelog down below)
- Removed: Windows portable (RosadinTV) ([#3535](https://github.com/streamlink/streamlink/pull/3535))
- Removed: plugin for micous.com ([#3457](https://github.com/streamlink/streamlink/pull/3457)), ntvspor.net ([#3485](https://github.com/streamlink/streamlink/pull/3485)), btsports ([#3636](https://github.com/streamlink/streamlink/pull/3636))
- Dependencies: set `websocket-client` to `>=0.58.0` ([#3634](https://github.com/streamlink/streamlink/pull/3634))

[Full changelog](https://github.com/streamlink/streamlink/compare/2.0.0...2.1.0)


## streamlink 2.0.0 (2020-12-22)

Release highlights:

- BREAKING: dropped support for Python 2 and Python 3.5 ([#3232](https://github.com/streamlink/streamlink/pull/3232), [#3269](https://github.com/streamlink/streamlink/pull/3269))
- BREAKING: updated the Python version of the Windows installer to 3.8 ([#3330](https://github.com/streamlink/streamlink/pull/3330))  
  Users of Windows 7 will need their system to be fully upgraded.
- BREAKING: removed all deprecated CLI arguments ([#3277](https://github.com/streamlink/streamlink/pull/3277), [#3349](https://github.com/streamlink/streamlink/pull/3349))
  - `--http-cookies`, `--http-headers`, `--http-query-params`
  - `--no-version-check`
  - `--rtmpdump-proxy`
  - `--cmdline`, `-c`
  - `--errorlog`, `-e`
  - `--errorlog-path`
  - `--btv-username`, `--btv-password`
  - `--crunchyroll-locale`
  - `--pixiv-username`, `--pixiv-password`
  - `--twitch-oauth-authenticate`, `--twitch-oauth-token`, `--twitch-cookie`
  - `--ustvnow-station-code`
  - `--youtube-api-key`
- BREAKING: replaced various subtitle muxing CLI arguments with `--mux-subtitles` ([#3324](https://github.com/streamlink/streamlink/pull/3324))
  - `--funimationnow-mux-subtitles`
  - `--pluzz-mux-subtitles`
  - `--rtve-mux-subtitles`
  - `--svtplay-mux-subtitles`
  - `--vimeo-mux-subtitles`
- BREAKING: sideloading faulty plugins will now raise an `Exception` ([#3366](https://github.com/streamlink/streamlink/pull/3366))
- BREAKING: changed trace logging timestamp format ([#3273](https://github.com/streamlink/streamlink/pull/3273))
- BREAKING/API: removed deprecated `Session` compat options ([#3349](https://github.com/streamlink/streamlink/pull/3349))
- BREAKING/API: removed deprecated custom `Logger` and `LogRecord` ([#3273](https://github.com/streamlink/streamlink/pull/3273))
- BREAKING/API: removed deprecated parameters from `HLSStream.parse_variant_playlist` ([#3347](https://github.com/streamlink/streamlink/pull/3347))
- BREAKING/API: removed `plugin.api.support_plugin` ([#3398](https://github.com/streamlink/streamlink/pull/3398))
- Added: new plugin for pluto.tv ([#3363](https://github.com/streamlink/streamlink/pull/3363))
- Added: support for HLS master playlist URLs to `--stream-url` / `--json` ([#3300](https://github.com/streamlink/streamlink/pull/3300))
- Added: `--ffmpeg-fout` for changing the output format of muxed streams ([#2892](https://github.com/streamlink/streamlink/pull/2892))
- Added: `--ffmpeg-copyts` and `--ffmpeg-start-at-zero` ([#3404](https://github.com/streamlink/streamlink/pull/3404), [#3413](https://github.com/streamlink/streamlink/pull/3413))
- Added: `--streann-url` for iframe referencing ([#3356](https://github.com/streamlink/streamlink/pull/3356))
- Added: `--niconico-timeshift-offset` ([#3425](https://github.com/streamlink/streamlink/pull/3425))
- Fixed: duplicate stream names in DASH inputs ([#3410](https://github.com/streamlink/streamlink/pull/3410))
- Fixed: youtube live playback ([#3268](https://github.com/streamlink/streamlink/pull/3268), [#3372](https://github.com/streamlink/streamlink/pull/3372), [#3428](https://github.com/streamlink/streamlink/pull/3428))
- Fixed: `--twitch-disable-reruns` ([#3375](https://github.com/streamlink/streamlink/pull/3375))
- Fixed: various plugins issues (see detailed changelog down below)
- Changed: `{filename}` variable in `--player-args` / `-a` to `{playerinput}` and made both optional ([#3313](https://github.com/streamlink/streamlink/pull/3313))
- Changed: and fixed `streamlinkrc` config file in the Windows installer ([#3350](https://github.com/streamlink/streamlink/pull/3350))
- Changed: MPV's automated `--title` argument to `--force-media-title` ([#3405](https://github.com/streamlink/streamlink/pull/3405))
- Changed: HTML documentation theme to [furo](https://github.com/pradyunsg/furo) ([#3335](https://github.com/streamlink/streamlink/pull/3335))
- Removed: plugins for `skai`, `kingkong`, `ellobo`, `trt`/`trtspor`, `tamago`, `streamme`, `metube`, `cubetv`, `willax`

[Full changelog](https://github.com/streamlink/streamlink/compare/1.7.0...2.0.0)


## streamlink 1.7.0 (2020-10-18)

Release highlights:

- Added: new plugins for micous.com, tv999.bg and cbsnews.com
- Added: new embedded ad detection for Twitch streams ([#3213](https://github.com/streamlink/streamlink/pull/3213))
- Fixed: a few broken plugins and minor plugin issues (see changelog down below)
- Fixed: arguments in config files were read too late before taking effect ([#3255](https://github.com/streamlink/streamlink/pull/3255))
- Fixed: Arte plugin returning too many streams and overriding primary ones ([#3228](https://github.com/streamlink/streamlink/pull/3228))
- Fixed: Twitch plugin error when stream metadata API response is empty ([#3223](https://github.com/streamlink/streamlink/pull/3223))
- Fixed: Zattoo login issues ([#3202](https://github.com/streamlink/streamlink/pull/3202))
- Changed: plugin request and submission guidelines ([#3244](https://github.com/streamlink/streamlink/pull/3244))
- Changed: refactored and cleaned up Twitch plugin ([#3227](https://github.com/streamlink/streamlink/pull/3227))
- Removed: `platform=_` stream token request parameter from Twitch plugin (again) ([#3220](https://github.com/streamlink/streamlink/pull/3220))
- Removed: plugins for itvplayer, aljazeeraen, srgssr and dingittv

[Full changelog](https://github.com/streamlink/streamlink/compare/1.6.0...1.7.0)


## streamlink 1.6.0 (2020-09-22)

Release highlights:

- Fixed: lots of broken plugins and minor plugin issues (see changelog down below)
- Fixed: embedded ads on Twitch with an ads workaround, removing pre-roll and mid-stream ads ([#3173](https://github.com/streamlink/streamlink/pull/3173))
- Fixed: read timeout error when filtering out HLS segments ([#3187](https://github.com/streamlink/streamlink/pull/3187))
- Fixed: twitch plugin logging incorrect low-latency status when pre-roll ads exist ([#3169](https://github.com/streamlink/streamlink/pull/3169))
- Fixed: crunchyroll auth logic ([#3150](https://github.com/streamlink/streamlink/pull/3150))
- Added: the `--hls-playlist-reload-time` parameter for customizing HLS playlist reload times ([#2925](https://github.com/streamlink/streamlink/pull/2925))
- Added: `python -m streamlink` invocation style support ([#3174](https://github.com/streamlink/streamlink/pull/3174))
- Added: plugin for mrt.com.mk ([#3097](https://github.com/streamlink/streamlink/pull/3097))
- Changed: yupptv plugin and replaced email+pass with id+token authentication ([#3116](https://github.com/streamlink/streamlink/pull/3116))
- Removed: plugins for vaughnlive, pandatv, douyutv, cybergame, europaplus and startv

[Full changelog](https://github.com/streamlink/streamlink/compare/1.5.0...1.6.0)


## streamlink 1.5.0 (2020-07-07)

A minor release with fixes for `pycountry==20.7.3` ([#3057](https://github.com/streamlink/streamlink/pull/3057)) and a few plugin additions and removals.

And of course the usual plugin fixes and upgrades, which you can see in the git shortlog down below. Thank you to everyone involved!

Support for Python2 has not been dropped yet (contrary to the comment in the last changelog), but will be in the near future.

[Full changelog](https://github.com/streamlink/streamlink/compare/1.4.1...1.5.0)


## streamlink 1.4.1 (2020-04-24)

No code changes. [See the full `1.4.0` changelog here.](https://github.com/streamlink/streamlink/releases/tag/1.4.0)

[Full changelog](https://github.com/streamlink/streamlink/compare/1.4.0...1.4.1)


## streamlink 1.4.0 (2020-04-22)

This will be the last release with support for Python 2, as it has finally reached its EOL at the beginning of this year.

Streamlink 1.4.0 comes with lots of plugin fixes/improvements, as well as some new features and plugins, and also a few plugin removals.

Notable changes:

- New: low latency streaming on Twitch via `--twitch-low-latency` ([#2513](https://github.com/streamlink/streamlink/pull/2513))
- New: output HLS segment data immediately via `--hls-segment-stream-data` ([#2513](https://github.com/streamlink/streamlink/pull/2513))
- New: always show download progress via `--force-progress` ([#2438](https://github.com/streamlink/streamlink/pull/2438))
- New: URL template support for `--hls-segment-key-uri` ([#2821](https://github.com/streamlink/streamlink/pull/2821))
- Removed: Twitch auth logic, `--twitch-oauth-token`, `--twitch-oauth-authenticate`, `--twitch-cookie` ([#2846](https://github.com/streamlink/streamlink/pull/2846))
- Fixed: Youtube plugin ([#2858](https://github.com/streamlink/streamlink/pull/2858))
- Fixed: Crunchyroll plugin ([#2788](https://github.com/streamlink/streamlink/pull/2788))
- Fixed: Pixiv plugin ([#2840](https://github.com/streamlink/streamlink/pull/2840))
- Fixed: TVplayer plugin ([#2802](https://github.com/streamlink/streamlink/pull/2802))
- Fixed: Zattoo plugin ([#2887](https://github.com/streamlink/streamlink/pull/2887))
- Changed: set Firefox User-Agent HTTP header by default ([#2795](https://github.com/streamlink/streamlink/pull/2795))
- Changed: upgraded bundled FFmpeg to `4.2.2` in Windows installer ([#2916](https://github.com/streamlink/streamlink/pull/2916))

[Full changelog](https://github.com/streamlink/streamlink/compare/1.3.1...1.4.0)


## streamlink 1.3.1 (2020-01-27)

A small patch release that addresses the removal of [MPV's legacy option syntax](https://mpv.io/manual/master/#legacy-option-syntax), also with fixes of several plugins, the addition of the `--twitch-disable-reruns` parameter and dropped support for Python 3.4.

[Full changelog](https://github.com/streamlink/streamlink/compare/1.3.0...1.3.1)


## streamlink 1.3.0 (2019-11-22)

A new release with plugin updates and fixes, including Twitch.tv (see [#2680](https://github.com/streamlink/streamlink/issues/2680)), which had to be delayed due to back and forth API changes.

The Twitch.tv workarounds mentioned in [#2680](https://github.com/streamlink/streamlink/issues/2680) don't have to be applied anymore, but authenticating via `--twitch-oauth-token` has been disabled, regardless of the origin of the OAuth token (via `--twitch-oauth-authenticate` or the Twitch website). In order to not introduce breaking changes, both parameters have been kept in this release and the user name will still be logged when using an OAuth token, but receiving item drops or accessing restricted streams is not possible anymore.

Plugins for the following sites have also been added:
  - albavision
  - news.now.com
  - twitcasting.tv
  - viu.tv
  - vlive.tv
  - willax.tv

[Full changelog](https://github.com/streamlink/streamlink/compare/1.2.0...1.3.0)


## streamlink 1.2.0 (2019-08-18)

Here are the changes for this month's release

- Multiple plugin fixes
- Fixed single hyphen params at the beginning of --player-args (#2333)
- `--http-proxy` will set the default value of `--https-proxy` to same as `--http-proxy`. (#2536)
- DASH Streams will handle headers correctly (#2545)
- the timestamp for FFMPEGMuxer streams will start with zero (#2559)

[Full changelog](https://github.com/streamlink/streamlink/compare/1.1.1...1.2.0)


## streamlink 1.1.1 (2019-04-02)

This is just a small patch release which fixes a build/deploy issue with the new special wheels for Windows on PyPI. (#2392)

[Please see the full changelog of the `1.1.0` release!](https://github.com/streamlink/streamlink/releases/tag/1.1.0)

[Full changelog](https://github.com/streamlink/streamlink/compare/1.1.0...1.1.1)


## streamlink 1.1.0 (2019-03-31)

These are the highlights of Streamlink's first minor release after the 1.0.0 milestone:

- several plugin fixes, improvements and new plugin implementations
- addition of the `--twitch-disable-ads` parameter for filtering out advertisement segments from Twitch.tv streams (#2372)
- DASH stream improvements (#2285)
- documentation enhancements (#2292, #2293)
- addition of the `{url}` player title variable (#2232)
- default player title config for PotPlayer (#2224)
- new `streamlinkw` executable on Windows (wheels + installer) (#2326)
- Github release assets simplification (#2360)

[Full changelog](https://github.com/streamlink/streamlink/compare/1.0.0...1.1.0)


## streamlink 1.0.0 (2019-01-30)

The celebratory release of Streamlink 1.0.0!

*A lot* of hard work has gone into getting Streamlink to where it is. Not only is Streamlink used across multiple applications and platforms, but companies as well. 

Streamlink started from the inaugural [fork of Livestreamer](https://github.com/chrippa/livestreamer/issues/1427) on September 17th, 2016. 

Since then, We've hit multiple milestones:

 - Over 886 PRs
 - Hit 3,000 commits in Streamlink
 - Obtaining our first sponsors as well as backers of the project
 - The creation of our own logo (https://github.com/streamlink/streamlink/issues/1123)

Thanks to everyone who has contributed to Streamlink (and our backers)! Without you, we wouldn't be where we are today.

**Without further ado, here are the changes in release 1.0.0:**

  - We have a new icon / logo for Streamlink! (https://github.com/streamlink/streamlink/pull/2165)
  - Updated dependencies (https://github.com/streamlink/streamlink/pull/2230)
  - A *ton* of plugin updates. Have a look at [this search query](https://github.com/streamlink/streamlink/pulls?utf8=%E2%9C%93&q=is%3Apr+is%3Aclosed+plugins.+) for all the recent updates.
  - You can now provide a custom key URI to override HLS streams (https://github.com/streamlink/streamlink/pull/2139). For example: `--hls-segment-key-uri <URI>`
  - User agents for API communication have been updated (https://github.com/streamlink/streamlink/pull/2194)
  - Special synonyms have been added to sort "best" and "worst" streams (https://github.com/streamlink/streamlink/pull/2127). For example: `streamlink --stream-sorting-excludes '>=480p' URL best,best-unfiltered`
  - Process output will no longer show if tty is unavailable (https://github.com/streamlink/streamlink/pull/2090)
  - We've removed BountySource in favour of our OpenCollective page. If you have any features you'd like to request, please open up an issue with the request and possibly consider backing us!
  - Improved terminal progress display for wide characters (https://github.com/streamlink/streamlink/pull/2032)
  - Fixed a bug with dynamic playlists on playback (https://github.com/streamlink/streamlink/pull/2096)
  - Fixed makeinstaller.sh (https://github.com/streamlink/streamlink/pull/2098)
  - Old Livestreamer deprecations and API references were removed (https://github.com/streamlink/streamlink/pull/1987)
  - Dependencies have been updated for Python (https://github.com/streamlink/streamlink/pull/1975)
  - Newer and more common User-Agents are now used (https://github.com/streamlink/streamlink/pull/1974)
  - DASH stream bitrates now round-up to the nearest 10, 100, 1000, etc. (https://github.com/streamlink/streamlink/pull/1995)
  - Updated documentation on issue templates (https://github.com/streamlink/streamlink/pull/1996)
  - URL have been added for better processing of HTML tags (https://github.com/streamlink/streamlink/pull/1675)
  - Fixed sort and prog issue (https://github.com/streamlink/streamlink/pull/1964)
  - Reformatted issue templates (https://github.com/streamlink/streamlink/pull/1966)
  - Fixed crashing bug with player-continuous-http option (https://github.com/streamlink/streamlink/pull/2234)
  - Make sure all dev dependencies (https://github.com/streamlink/streamlink/pull/2235)
  - -r parameter has been replaced for --rtmp-rtmpdump (https://github.com/streamlink/streamlink/pull/2152)

**Breaking changes:**

  - A large number of unmaintained or NSFW plugins have been removed. You can find the PR that implemented that change here: https://github.com/streamlink/streamlink/pull/2003 . See our [CONTRIBUTING.md](https://github.com/streamlink/streamlink/blob/130489c6f5ad15488cd4ff7a25c74bf070f163ec/CONTRIBUTING.md) documentation for plugin policy.

[Full changelog](https://github.com/streamlink/streamlink/compare/0.14.2...1.0.0)


## streamlink 0.14.2 (2018-06-28)

Just a few small fixes in this release. 

- Fixed Twitch OAuth request flow (https://github.com/streamlink/streamlink/pull/1856)
- Fix the tv3cat and vk plugins (https://github.com/streamlink/streamlink/pull/1851, https://github.com/streamlink/streamlink/pull/1874)
- VOD supported added to atresplayer plugin (https://github.com/streamlink/streamlink/pull/1852, https://github.com/streamlink/streamlink/pull/1853)
- Removed tv8cati and nineanime plugins (https://github.com/streamlink/streamlink/pull/1860, https://github.com/streamlink/streamlink/pull/1863)
- Added mjunoon.tv plugin (https://github.com/streamlink/streamlink/pull/1857)

[Full changelog](https://github.com/streamlink/streamlink/compare/0.14.0...0.14.2)


## streamlink 0.14.0 (2018-06-26)

Here are the changes to this months release!

- Multiple plugin fixes
- Bug fixes for DASH streams (https://github.com/streamlink/streamlink/pull/1846)
- Updated API call for api.utils hours_minutes_seconds (https://github.com/streamlink/streamlink/pull/1804)
- Updated documentation (https://github.com/streamlink/streamlink/pull/1826)
- Dict structures fix (https://github.com/streamlink/streamlink/pull/1792)
- Reformated help menu (https://github.com/streamlink/streamlink/pull/1754)
- Logger fix (https://github.com/streamlink/streamlink/pull/1773)

[Full changelog](https://github.com/streamlink/streamlink/compare/0.13.0...0.14.0)


## streamlink 0.13.0 (2018-06-06)

Massive release this month!

Here are the changes:
 - Initial MPEG DASH support has been added! (https://github.com/streamlink/streamlink/pull/1637) Many thanks to @beardypig
 - As always, a *ton* of plugin updates
 - Updates to our documentation (https://github.com/streamlink/streamlink/pull/1673)
 - Updates to our logging (https://github.com/streamlink/streamlink/pull/1752) as well as log --quiet options (https://github.com/streamlink/streamlink/pull/1744) (https://github.com/streamlink/streamlink/pull/1720)
 - Our release script has been updated (https://github.com/streamlink/streamlink/pull/1711)
 - Support for livestreams when using the `--hls-duration` option (https://github.com/streamlink/streamlink/pull/1710)
 - Allow streamlink to exit faster when using Ctrl+C (https://github.com/streamlink/streamlink/pull/1658)
 - Added an OpenCV Face Detection example (https://github.com/streamlink/streamlink/pull/1689)

[Full changelog](https://github.com/streamlink/streamlink/compare/0.12.1...0.13.0)


## streamlink 0.12.1 (2018-05-07)

Streamlink 0.12.1

Small release to fix a pip / Windows.exe generation bug!

[Full changelog](https://github.com/streamlink/streamlink/compare/0.12.0...0.12.1)


## streamlink 0.12.0 (2018-05-07)

Streamlink 0.12.0

Thanks for all the contributors to this month's release!

New updates:

  - A *ton* of plugin updates (like always! see below for a list of updates)
  - Ignoring a bunch of useless files when developing (https://github.com/streamlink/streamlink/pull/1570)
  - A new option to limit the number of fetch retries (https://github.com/streamlink/streamlink/pull/1375)
  - YouTube has been updated to not use MuxedStream for livestreams (https://github.com/streamlink/streamlink/pull/1556)
  - Bug fix with ffmpegmux (https://github.com/streamlink/streamlink/pull/1502)
  - Removed dead plugins and deprecated options (https://github.com/streamlink/streamlink/pull/1546)

[Full changelog](https://github.com/streamlink/streamlink/compare/0.11.0...0.12.0)


## streamlink 0.11.0 (2018-03-08)

Streamlink 0.11.0!

Here's what's new:

  - Fixed documentation (https://github.com/streamlink/streamlink/pull/1467 and https://github.com/streamlink/streamlink/pull/1468)
  - Current versions of the OS, Python, Streamlink and Requests are now shown with -l debug (https://github.com/streamlink/streamlink/pull/1374)
  - ok.ru/live plugin added (https://github.com/streamlink/streamlink/pull/1451)
  - New option --hls-segment-ignore-names (https://github.com/streamlink/streamlink/pull/1432)
  - AfreecaTV plugin updates (https://github.com/streamlink/streamlink/pull/1390)
  - Added support for zattoo recordings (https://github.com/streamlink/streamlink/pull/1480)
  - Bigo plugin updates (https://github.com/streamlink/streamlink/pull/1474)
  - Neulion plugin removed due to DMCA notice (https://github.com/streamlink/streamlink/pull/1497)
  - And many more updates to numerous other plugins!

[Full changelog](https://github.com/streamlink/streamlink/compare/0.10.0...0.11.0)


## streamlink 0.10.0 (2018-01-23)

Streamlink 0.10.0!

There's been a lot of activity since our November release.

Changes:

  - Multiple plugin updates (too many to list, see below for the plugin changes!)
  - HLS seeking support (https://github.com/streamlink/streamlink/pull/1303)
  - Changes to the Windows binary (docs: https://github.com/streamlink/streamlink/pull/1408 minor changes to install directory: https://github.com/streamlink/streamlink/pull/1407)

[Full changelog](https://github.com/streamlink/streamlink/compare/0.9.0...0.10.0)


## streamlink 0.9.0 (2017-11-14)

Streamlink 0.9.0 has been released!

This release is mostly code refactoring as well as module inclusion.

Features:

  - Updates to multiple plugins (electrecetv, tvplayer, Teve2, cnnturk, kanald)
  - SOCKS module being included in the Streamlink installer (PySocks)

Many thanks to those who've contributed in this release!

[Full changelog](https://github.com/streamlink/streamlink/compare/0.8.1...0.9.0)


## streamlink 0.8.1 (2017-09-12)

0.8.1 of Streamlink!

97 commits have occurred since the last release, including a large majority of plugin changes.

Here's the outline of what's new:

  - Multiple plugin fixes (twitch, vaughlive, hitbox, etc.)
  - Donations! We've gone ahead and joined the Open Collective at https://opencollective.com/streamlink
  - Multiple doc updates
  - Support for SOCKS proxies
  - Code refactoring

Many thanks to those who've contributed in this release!

[Full changelog](https://github.com/streamlink/streamlink/compare/0.7.0...0.8.1)


## streamlink 0.7.0 (2017-06-30)

0.7.0 of Streamlink!

Since our May release, we've incorporated quite a few changes!

Outlined are the major features in this month's release:

  - Stream types will now be sorted accordingly in terms of quality
  - TeamLiquid.net Plugin added
  - Numerous plugin & bug fixes
  - Updated HomeBrew package
  - Improved CLI documentation

Many thanks to those who've contributed in this release!

If you think that this application is helpful, please consider supporting the maintainers by [donating](https://streamlink.github.io/donate.html).

[Full changelog](https://github.com/streamlink/streamlink/compare/0.6.0...0.7.0)


## streamlink 0.6.0 (2017-05-11)

Another release of Streamlink!

We've updated more plugins, improved documentation, and moved out nightly builds to Bintray (S3 was costing *wayyyy* too much).

Again, many thanks for those who've contributed!

Thank you very much!

[Full changelog](https://github.com/streamlink/streamlink/compare/0.5.0...0.6.0)


## streamlink 0.5.0 (2017-04-04)

Streamlink 0.5.0!

Lot's of contributions since the last release. As always, lot's of updating to plugins!

One of the new features is the addition of Google Drive / Google Docs, you can now stream videos stored on Google Docs.

We've also gone ahead and removed dead plugins (sites which have gone down) as well as added pycrypto as a dependency for future plugins.

Again, many thanks for those who have contributed!

Thank you very much!

[Full changelog](https://github.com/streamlink/streamlink/compare/0.4.0...0.5.0)


## streamlink 0.4.0 (2017-03-09)

0.4.0 of Streamlink!

114 commits since the last release and *a lot* has changed.

In general, we've added some localization as well as an assortment of new plugins.

We've also introduced a change for Streamlink to *not* check for new updates each time Streamlink starts. We found this feature annoying as well as delaying the initial start of the stream. This feature can be re-enabled by the command line.

The major features of this release are:

  - New plugins added
  - Ongoing support to current plugins via bug fixes
  - Ensure retries to HLS streams
  - Disable update check

Many thanks to all contributors who have contributed in this release!

[Full changelog](https://github.com/streamlink/streamlink/compare/0.3.2...0.4.0)


## streamlink 0.3.2 (2017-02-10)

0.3.2 release of Streamlink!

A minor bug release of 0.3.2 to fix a few issues with stream providers.

Thanks to all whom have contributed to this (tiny) release!

[Full changelog](https://github.com/streamlink/streamlink/compare/0.3.1...0.3.2)


## streamlink 0.3.1 (2017-02-03)

0.3.1 release of Streamlink

A *minor* release, we update our source code upload to *not* include the ffmpeg.exe binary as well as update a multitude of plugins.

Thanks again for all the contributions as well as updates!

[Full changelog](https://github.com/streamlink/streamlink/compare/0.3.0...0.3.1)


## streamlink 0.3.0 (2017-01-24)

Release 0.3.0 of Streamlink!

A lot of updates to each plugin (thank you @beardypig !), automated Windows releases, PEP8 formatting throughout Streamlink are some of the few updates to this release as we near a stable 1.0.0 release.

Main features are:

  - Lot's of maintaining / updates to plugins
  - General bug and doc fixes
  - Major improvements to development (github issue templates, automatically created releases)

[Full changelog](https://github.com/streamlink/streamlink/compare/0.2.0...0.3.0)


## streamlink 0.2.0 (2016-12-16)

Release 0.2.0 of Streamlink!

We've done numerous changes to plugins as well as fixed quite a few
which were originally failing. Among these changes are updated docs as
well as general UI/UX cleaning with console output.

The main features are:

 - Additional plugins added
 - Plugin fixes
 - Cleaned up console output
 - Additional documentation (contribution, installation instructions)

Again, thank you everyone whom contributed to this release! :D

[Full changelog](https://github.com/streamlink/streamlink/compare/0.1.0...0.2.0)


## streamlink 0.1.0 (2016-11-21)

A major update to Streamlink.

With this release, we include a Windows binary as well as numerous
plugin changes and fixes.

The main features are:

 -  Windows binary (and generation!) thanks to the fabulous work by
 @beardypig
 -  Multiple plugin fixes
 -  Remove unneeded run-as-root (no more warning you when you run as
   root, we trust that you know what you're doing)
 -  Fix stream quality naming issue

[Full changelog](https://github.com/streamlink/streamlink/compare/0.0.2...0.1.0)


## streamlink 0.0.2 (2016-10-12)

The second ever release of Streamlink!

In this release we've not only set the stepping stone for the further
development of Streamlink (documentation site updated, CI builds
working) but we're already fixing bugs and implementing features past
the initial fork of livestreamer.

The main features of this release are: - New windows build available and
generated via pyinstaller - Multiple provider bug fixes (twitch,
picarto, itvplayer, crunchyroll, periscope, douyutv) - Updated and
reformed documentation which also includes our site
https://streamlink.github.io

As always, below is a `git shortlog` of all changes from the previous
release of Streamlink (0.0.1) to now (0.0.2).

[Full changelog](https://github.com/streamlink/streamlink/compare/0.0.1...0.0.2)


## streamlink 0.0.1 (2016-09-23)

The first release of Streamlink!

This is the first release from the initial fork of Livestreamer. We aim
to have a concise, fast review process and progress in terms of
development and future releases.

Below is a `git shortlog` of all commits since the last change within
Livestream (hash ab80dbd6560f6f9835865b2fc9f9c6015aee5658). This will
serve as a base-point as we continue development of "Streamlink".

New releases will include a list of changes as we add new features /
code refactors to the existing code-base.

[Full changelog](https://github.com/streamlink/streamlink/compare/ab80dbd...0.0.1)
