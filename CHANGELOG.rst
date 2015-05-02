Version 1.12.2 (2015-05-02)
---------------------------

Bug fixes:
 - hds: Don't modify request params when handling PVSWF. (#842)
 - hls: Handle unpadded encryption IV's.
 - Fixed regression in redirect resolver. (#816)

Plugins:
 - Added plugin for media.ccc.de (media_ccc_de), patch by @meise.
 - Added plugin for Kanal 5/9/11 (sbsdiscovery), patch by @tboss. (#815)
 - Added plugin for Periscope (periscope).
 - Added plugin for SSH101 (ssh101), patch by @Razier-23. (#869)
 - artetv: Updated for service changes.
 - crunchyroll: Updated for service changes. (#864, #865)
 - hitbox: Fixed VOD support. (#856)
 - livestream: Updated for service changes.
 - viasat: Added support for juicyplay.se.
 - viasat: Fixed missing streams. (#822)
 - youtube: Added support for /channel URLs. (#825)


Version 1.12.1 (2015-03-22)
---------------------------

Bug fixes:
 - Don't crash when failing to look up listening ports. (#790)

Plugins:
 - Added plugin for ITV Player, patch by @blxd. (#776)
 - Added plugin for tv3.cat, patch by @blxd. (#784)
 - Added plugin for TV Catchup, patch by @blxd. (#775)
 - connectcast: Fixed crash, patch by @mammothb. (#779)
 - dailymotion: Added support for HDS VODs. (#731)
 - gaminglive: Added support for VODs, patches by @kasper93 and @chhe. (#789, #808)
 - picarto: Updated for service changes, patch by @FireDart. (#803)
 - tv4play: Work around bad SSL implementation on Python 2. (#785)
 - twitch: Use correct OAuth scopes, patch by @josephglanville. (#778)
 - ustreamtv: Updated for service changes, patch by @trUSTssc. (#799)
 - viasat: Fixed missing streams. (#750)
 - viasat: Added play.tv3.lt to supported URLs. (#773)

Streams:
 - hds: Fixed issue with query parameters when building fragment URLs. (#786)


Version 1.12.0 (2015-03-01)
---------------------------

Bug fixes:
 - Made HTTP modes more strict to avoid issues with `mpv --yt-dl`.
 - Fixed :option:`--http-cookie` option crash.

CLI:
 - Added :option:`--can-handle-url` option, useful for scripting.
 - Added :option:`--version-check` option to force a version check.
 - Added a passive HTTP server mode (:option:`--player-external-http`), patch by @danielkza. (#699)

Plugins:
 - Added plugin for Disney Channel Germany, patch by @boekkooi. (#698)
 - Added plugin for NOS (Nederlandse Omroep Stichting), patch by @boekkooi. (#697)
 - Added plugin for tga.plu.cn, patch by @wolftankk. (#669)
 - Added plugin for Wat.tv, patch by @boekkooi. (#701)
 - Added plugin for afreeca.tv. (The old afreecatv plugin has been renamed to afreeca)
 - chaturbate: Added support for subdomain URLs, patch by @GameWalker. (#676)
 - connectcast: Updated for service changes, patch by @darvelo. (#722)
 - dailymotion: Added support for games.dailymotion.com, patch by @daslicious. (#684)
 - dommune: Fixed Youtube redirect URL.
 - gaminglive: Updated for service changes, patch by @chhe. (#721)
 - mlgtv: Updated for service changes, patch by @daslicious. (#686)
 - hitbox: Updated for services changes. (#648)
 - streamlive: Updated for service changes, patch by @daslicious. (#667)
 - ustreamtv: Updated for service changes. (#707)
 - youtube: Now handles more URL types.


Version 1.11.1 (2014-12-12)
---------------------------

Plugins:
 - twitch: Updated for API changes. (#633)


Version 1.11.0 (2014-12-10)
---------------------------

Bugfixes:
 - cli: Only apply the backslash magic on player paths on Windows.

CLI:
 - Added :option:`--http-cookie` option.
 - Added :option:`--http-header` option.
 - Added :option:`--http-query-param` option.
 - Deprecated the :option:`--http-cookies` option.
 - Deprecated the :option:`--http-headers` option.
 - Deprecated the :option:`--http-query-params` option.
 - Changed the continuous HTTP mode to always fetch streams.
   Should fix segmented streams repeating at the end for most
   services.

Plugins:
 - Added plugin for NPO, patch by @monkeyphysics. (#599)
 - afreecatv: Updated for service changes. (#568)
 - beattv: Updated validation schema to include float offsets, patch by @suhailpatel. (#555)
 - douyutv: Added support for transcodes.
 - gaminglive: Fixed quality names, patch by @chhe. (#545)
 - goodgame: Updated for service changes, patch by @JaxxC. (#554)
 - oldlivestream: Check that streams don't return 404. (#560)
 - ilive: Updated for service changes and renamed to streamlive. (#563)
 - livestation: Updated for service changes. (#581)
 - twitch: Added support for the new video streams.
 - vaughnlive: Updated for service changes. (#611)
 - veetle: Fixed shortcut URLs, patch by @monkeyphysics. (#601)
 - viasat/viagame: Updated for service changes (#564, #566, #617)

Plugin API:
 - Added a class to simplify mapping data to stream objects.


Version 1.10.2 (2014-09-05)
---------------------------

Plugins:
 - Added plugin for Arte.tv (artetv). (#457)
 - Added plugin for RTVE.es (rtve), patch by @jaimeMF. (#509)
 - Added plugin for Seemeplay.ru (seemeplay). (#510)
 - euronews: Updated for service changes.
 - filmon: Updated for service changes. (#514)
 - gaminglive: Updated for service changes, patch by @chhe. (#524)
 - twitch: Now handles videos with chunks that are missing URLs.
 - vaughnlive: Added support for breakers.tv, instagib.tv and vapers.tv. (#521)
 - youtube: Added support for audio-only streams. (#522)


Version 1.10.1 (2014-08-22)
---------------------------

Bug fixes:
 - Fixed strange read error caused by double buffering in FLV playlists.

Plugins:
 - Added plugin for Vaughn Live (vaughnlive). (#478)


Version 1.10.0 (2014-08-18)
---------------------------

Bug fixes:
 - The HDS options added in 1.8.0 where never actually applied when
   used via the CLI, oops.
 - Fixed default player paths not expanding ~, patch by @medina. (#484)

CLI:
 - Added :option:`--hds-segment-threads` option.
 - Added :option:`--hls-segment-threads` option.
 - Added :option:`--stream-segment-attempts` option.
 - Added :option:`--stream-segment-threads` option.
 - Added :option:`--stream-segment-timeout` option.
 - Added :option:`--stream-timeout` option.
 - Deprecated the :option:`--jtv-cookie` option.
 - Deprecated the :option:`--jtv-password` option.
 - Significantly improved the status line printed while writing a
   stream to a file. (#462)

Plugins:
 - Added plugin for goodgame.ru (goodgame), patch by @eltiren. (#466)
 - Added plugin for gaminglive.tv (gaminglive), patch by @chhe. (#468)
 - Added plugin for douyutv.com (douyutv), patch by @nixxquality. (#469)
 - Added plugin for NHK World (nhkworld).
 - Added plugin for Let On TV (letontv), patch by @cheah. (#500)
 - Removed plugin: justintv.
 - afreecatv: Updated for service changes. (#488)
 - hitbox: Added support for HLS videos.
 - twitch: Fixed some Twitch broadcasts being unplayable. (#490)
 - ustreamtv: Fixed regression that caused channels using RTMP streams to fail.

Streams:
 - akamaihd: Now supports background buffering.
 - http: Now supports background buffering.

API:
 - Added new session option: ``hds-segment-threads``.
 - Added new session option: ``hls-segment-threads``.
 - Added new session option: ``stream-segment-attempts``.
 - Added new session option: ``stream-segment-threads``.
 - Added new session option: ``stream-segment-timeout``.
 - Added new session option: ``stream-timeout``.


Version 1.9.0 (2014-07-22)
--------------------------

General:
 - **Dropped support for Python 3.2.** This is due to missing features
   which are necessary for this projects progression.
 - `singledispatch <https://pypi.python.org/pypi/singledispatch>`_ is now a
   dependency on Python <3.4.

Bug fixes:
 - Handle bad input data better in parse_json/xml. (#440)
 - Handle bad input data in config files. (#432)
 - Fixed regression causing rtmpdump proxies to have no effect.

CLI:
 - Improved :option:`--help` significantly, more readable and more content.
 - Added :option:`--config` option.
 - Added :option:`--stream-url` option. (#281)
 - Added support for K and M suffixes to the :option:`--ringbuffer-size` option.
 - Added support for loading config files based on plugin.
 - Added ~/Applications to the search path for VLC on Mac OS X, patch by @maxnordlund. (#454)
 - Deprecated :option:`--best-stream-default` and added :option:`--default-stream`
   as a more flexible replacement. (#381)
 - Will now only warn about newer versions available every 6 hours.

Plugins:
 - Many plugins have been refactored to use the validation API and better coding standards.
 - Added plugin for Aftonbladet (aftonbladet).
 - Added plugin for ARD Live (ard_live), patch by @MasterofJOKers. (#419)
 - Added plugin for ARD Mediathek (ard_mediathek), patch by @yeeeargh. (#421)
 - Added plugin for Connect Cast (connectcast). (#423)
 - Added plugin for Danmarks Radio (drdk).
 - Added plugin for DOMMUNE (dommune).
 - Added plugin for TV4 Play (tv4play).
 - Added plugin for VGTV (vgtv), patch by @jantore. (#435)
 - Removed plugin: cast3d
 - Removed plugin: freedocast
 - Removed plugin: hashd
 - Removed plugin: ongamenet
 - afreecatv: Updated for service changes. (#412, #413)
 - dailymotion: Added support for source streams, patch by @kasper93. (#428)
 - euronews: Added support for videos.
 - nrk: Added support for radio.nrk.no, patch by @jantore. (#433)
 - picarto: Updated for service changes. (#431)
 - twitch: Added support for audio only streams, patch by @CommanderRoot. (#411)
 - viasat: Added support for HDS streams.
 - viasat: Added support for viagame.com.

API:
 - Added :func:`Livestreamer.streams` method.
 - Added :func:`livestreamer.streams` function.
 - Renamed :func:`Plugin.get_streams` to :func:`Plugin.streams`.

Plugin API:
 - Added a validation API to make validating data easier and safer.


Version 1.8.2 (2014-05-30)
--------------------------

Bug fixes:
 - Fixed regression in loading config from non-ascii paths on Python 2.

Plugins:
 - azubutv: Update for service changes, patch by Gapato. (#399)
 - dailymotion: Added support for VODs, patch by Gapato. (#402)
 - hitbox: Fixed a issue where the correct streaming server was not used.

Streams:
 - hls: Handle playlists that redirect. (#405)


Version 1.8.1 (2014-05-18)
--------------------------

General:
 - Added a wheel package to PyPi for speedier installation via pip.

Bug fixes:
 - hls: Handle encrypted segments that are invalid length (not multiple by 16). (#365)

Plugins:
 - Added plugin for Furstream, patch by Pascal Romahn. (#360)
 - Added plugin for Viasat's play sites (tv6play.se, etc). (#378)
 - Added plugin for ZDFmediathek, patch by Pascal Romahn. (#360)
 - azubutv: Updated for service changes. (#373)
 - crunchyroll: Correctly handle unicode errors, patch by Agustin Carrasco. (#387, #388)
 - filmon: Updated for service changes, patch by Athanasios Oikonomou. (#375)
 - hitbox: Updated for service changes.
 - ilive: Updated for service changes, patch by Athanasios Oikonomou. (#376)
 - svtplay: Added support for SVT Flow.
 - twitch: Now uses the beta API on beta.twitch.tv URLs. (#391)
 - ustream: Correctly handle UHS streams containing only video or audio.


Version 1.8.0 (2014-04-21)
--------------------------

CLI:
 - Added option: ``--no-version-check``
 - Added HTTP options: ``--http-cookies``,
   ``--http-headers``,
   ``--http-query-params``,
   ``--http-ignore-env``,
   ``--http-no-ssl-verify``,
   ``--http-ssl-cert``,
   ``--http-ssl-cert-crt-key`` and
   ``--http-timeout``
 - Added HTTP stream option: ``--http-stream-timeout``
 - Added HDS stream options: ``--hds-segment-attempts``,
   ``--hds-segment-timeout``
   ``--hds-timeout``
 - Added HLS stream options: ``--hls-live-edge``,
   ``--hls-segment-attempts``,
   ``--hls-segment-timeout`` and
   ``--hls-timeout``
 - Added RTMP stream option: ``--rtmp-timeout``
 - Added plugin options: ``--livestation-email`` and ``--livestation-password``
 - Added stream options: ``--retry-streams``,
   ``--retry-open`` and
   ``--best-stream-default``
 - Deprecated option: ``--hds-fragment-buffer``

Plugins:
 - Added plugin for Bambuser, patch by Athanasios Oikonomou. (#327)
 - Added plugin for Be-at.tv, patch by Athanasios Oikonomou. (#342)
 - Added plugin for Chaturbate, patch by papplampe. (#337)
 - Added plugin for Cybergame.tv, patch by Athanasios Oikonomou. (#324)
 - Added plugin for Picarto, patch by papplampe. (#352)
 - Added plugin for SpeedRunsLive, patch by Stefan Breunig. (#335)
 - Removed plugins for dead services: Owncast.me and YYCast.
 - azubutv: Added support for beta.azubu.tv.
 - crunchyroll: Added workaround for SSL verification issue.
 - dailymotion: Added support for HDS streams. (#348)
 - gomexp: Fixed encoding issue on Python 2.
 - livestation: Added support for logging in, patch by Sunaga Takahiro. (#344)
 - mlgtv: Removed the ``mobile_`` prefix from the HLS streams.
 - twitch: Added workaround for SSL verification issue. (#255)
 - ustreamtv: Improved UHS stream stability.
 - ustreamtv: Added support for RTMP VODs.
 - youtube: Updated for service changes.
 - youtube: Added support for embed URLs, patch by Athanasios Oikonomou.
 - youtube: Now only picks up live streams from channel pages.

General:
 - Now attempts to resolve URL redirects such as URL shorterners.

Bug fixes:
 - Added workaround for HTTP streams not applying read timeout on some requests versions.

API:
 - Added new options: ``hds-segment-attempts``,
   ``hds-segment-timeout``,
   ``hds-timeout``,
   ``hls-live-edge``,
   ``hls-segment-attempts``,
   ``hls-segment-timeout``,
   ``hls-timeout``,
   ``http-proxy``,
   ``https-proxy``,
   ``http-cookies``,
   ``http-headers``,
   ``http-query-params``,
   ``http-trust-env``,
   ``http-ssl-verify``,
   ``http-ssl-cert``,
   ``http-timeout``,
   ``http-stream-timeout`` and
   ``rtmp-timeout``
 - Renamed option ``errorlog`` to ``subprocess-errorlog``.
 - Renamed option ``rtmpdump-proxy`` to ``rtmp-proxy``.
 - Renamed option ``rtmpdump`` to ``rtmp-rtmpdump``.


Version 1.7.5 (2014-03-07)
--------------------------

Plugins:
 - filmon: Added VOD support, patch by Athanasios Oikonomou.
 - ilive: Added support for HLS streams, patch by Athanasios Oikonomou.
 - mlgtv: Updated for service changes.
 - veetle: Now handles shortened URLs, patch by Athanasios Oikonomou.
 - youtube: Updated for service changes.

Bug fixes:
 - Fixed gzip not getting decoded in streams.

Other:
 - Added scripts to automatically create Windows builds via Travis CI.
   Builds are available here: http://livestreamer-builds.s3.amazonaws.com/builds.html


Version 1.7.4 (2014-02-28)
--------------------------

Plugins:
 - Added plugin for MLG.tv. (#275)
 - Added plugin for DMCloud, patch by Athanasios Oikonomou. (#297)
 - Added plugin for NRK TV, patch by Jon Bergli Heier. (#309)
 - Added plugin for GOMeXP.com.
 - Removed GOMTV.net plugin as the service no longer exists.
 - mips: Fixed issue with case sensitive playpath. (#306)
 - ilive: Added missing app parameter. (#293)
 - ustreamtv: Added support for password protected streams via ``--ustream-password``.
 - youtube: Now handles youtu.be shortcuts, patch by Andy Mikhailenko. (#288)
 - youtube: Use first available stream found on channel pages, patch by "unintended". (#291)

Streams:
 - hds: Fixed segmented streams logic, patch by Moritz Blanke.

Bug fixes:
 - Fixed buffer overwriting issue when passing a memoryview, patch by Martin Panter. (#295)
 - Avoid a ResourceWarning when using ``--player-continuous-http``, patch by Martin Panter. (#296)


Version 1.7.3 (2014-01-31)
--------------------------

Plugins:
 - Added plugin for hitbox.tv, patch by t0mm0. (#248)
 - Added plugin for Crunchyroll, patch by Agustín Carrasco. (#262)
 - twitch: Added support for hours in ?t=... on VODs.
 - twitch: Added support for ?t=... on VOD highlights.

Streams:
 - hls: Now allows retries on failed segment fetch.

Bug fixes:
 - cli: Don't pass our proxy settings to the player. (#260)
 - hds: Now uses global height as stream name if needed when parsing manifests.
 - hls: Always use first stream for each quality in variant playlists. (#256)
 - hls: Now returns correct exception on playlist parser errors.
 - hls: Now remembers cookies set by variant playlist response. (#258)


Version 1.7.2 (2013-12-17)
--------------------------

CLI:
 - The ``--twitch-legacy-names`` option is now deprecated.
 - Added ``--twitch-oauth-authenticate`` and ``--twitch-oauth-token`` options.

Plugins:
 - filmon: Added quality weights. (#239)
 - filmon_us: Added support for VODs, patch by John Peterson. (#237)
 - twitch: Updated for service changes. No more RTMP streams, only HLS.
 - twitch: Removed mobile streams since they are the same as the new desktop streams.
 - twitch: Removed the legacy names option.
 - twitch: Added support for OAuth2 authentication.
 - twitch: Added support for the t=00m0s parameter in VOD URLs.

Bug fixes:
 - Always wait for the player process to exit, patch by Martin Panter. (#234)
 - Fixed potential deadlocking when using named pipe, patch by Martin Panter. (#236)
 - Fixed issue with spaces in default player path, patch by John Peterson. (#237)


Version 1.7.1 (2013-12-07)
--------------------------

Plugins:
 - Added FilmOn Social TV plugin by John Peterson. (#225)
 - twitch: Support mobile_source quality, patch by Andrew Bashore.

Streams:
 - hds: Will now use video height as stream names if available.
 - hds: Removed the use of movie identifier in the fragment URLs.
 - hds: Added support for player verification, patch by Martin Panter. (#222)

Bug fixes:
 - Fixed various Python warnings, patch by Martin Panter. (#221)
 - cli: Fixed back-slash issue in ``--player-args``. (#218)
 - hds: Fixed some streams complaining about the hardcoded hdcore parameter.
 - hls: Fixed live streams that keep all previous segments in the playlists. (#224)
 - setup.py now forces requests 1.x on Python <2.6.3. (#219)


Version 1.7.0 (2013-11-07)
--------------------------

CLI:
 - Added a ``--player-no-close`` option.
 - Added options to use HTTP proxies with ``--http-proxy`` and ``--https-proxy``.
 - It's now possible to specify multiple streams as a comma-separated
   list. If a stream is not available the next one in the list will be tried.
 - Now only resolves synonyms once when using ``--player-continuous-http``.
 - Removed the ``-u`` shortcut for ``--plugins``. This is a response to someone
   spreading the misinformation that ``-url`` is a sane parameter to use.
   It's technically valid, but due to the ``-u`` shortcut it would be
   interpreted by Python's argparse as ``--plugins --rtmpdump l`` which
   would cause livestreamer to look for a non-existing rtmpdump executable,
   thus disabling any RTMP streams. (#193)

Plugins:
 - Added Afreeca.tv plugin.
 - dailymotion: Fixed incorrect RTMP parameters. (#201)
 - filmon: Updated after service changes. Patch by Athanasios Oikonomou. (#205)
 - ilive: Updated after service changes. (#200)
 - livestream: Added support for HLS streams.
 - livestream: Updated after service changes. (#195)
 - mips: Updated after service changes. (#200)
 - svtplay: Fixed some broken HDS streams. (#200)
 - twitch: Updated to use the new HLS API.
 - weeb: Updated after service changes. Patch by Athanasios Oikonomou. (#207)
 - youtube: Now handles 3D streams properly. (#202)

Streams:
 - hds: Added support for global bootstraps.
 - hls: Rewrote the playlist parser from scratch to be more solid and correct
   in accordance to the latest M3U8 spec.
 - hls: Now supports playlists using EXT-X-BYTERANGE.
 - hls: Now supports playlists using multiple EXT-X-KEY tags.
 - hls: Now accepts extra requests parameters to be used when doing
   HTTP requests.

Bug fixes:
 - Fixed bytes-serialization when using ``--json``.


Version 1.6.1 (2013-10-07)
--------------------------

Bug fixes:
 - CLI: Fixed broken ``--player-http`` and ``--player-continuous-http`` on Windows.
 - CLI: Fixed un-quoted player paths containing backslashes being broken.


Version 1.6.0 (2013-09-29)
--------------------------

General:
 - All stream names are now forced to lowercase to avoid issues with
   services renaming streams. (#179)
 - Updated requests compatibility to 2.0. (#183)

Plugins:
 - Added plugin for Hashd.tv by kasper93. (#184)
 - Azubu.tv: Updated after service changes. (#170)
 - ILive.to: Updated after service changes. (#182)
 - Twitch/Justin.tv: Refactored and split into separate plugins.
    - Added support for archived streams (VOD). (#70)
    - Added a option to force legacy stream names (720p, 1080p+, etc).
    - Added a option to access password protected streams.
 - UStream.tv: Refactored plugin and added support for their RTMP API and
   special streaming technology (UHS). (#144)

CLI:
 - Added some more player options: ``--player-args``, ``--player-http``,
   ``--player-continuous-http`` and ``--player-passthrough``. (#131)
 - Expanded ``--stream-sorting-excludes`` to support more advanced
   filtering. (#159)
 - Now notifies the user if a new version of Livestreamer is available.
 - Now allows case-insensitive stream name lookup.

API:
 - Added a new exception (``LivestreamerError``) that all other exceptions
   inherit from.
 - The ``sorting_excludes`` parameter in ``Plugin.get_streams``
   now supports more advanced filtering. (#159)

Bug fixes:
 - Fixed HTTPStream with headers breaking ``--json`` on Python 3.


Version 1.5.2 (2013-08-27)
--------------------------

Plugins:
 - Twitch/Justin.tv: Fix stream names.


Version 1.5.1 (2013-08-13)
--------------------------

Plugins:
 - Added plugin for Filmon.
 - Twitch/Justin.tv: Safer cookie and SWF URL handling.
 - Youtube: Enable VOD support.

Bug fixes:
 - Fixed potential crash when invalid UTF-8 is passed as arguments
   to subprocesses.


Version 1.5.0 (2013-07-18)
--------------------------

CLI:
 - Handle SIGTERM as SIGINT.
 - Improved default player (VLC) detection.
 - --stream-priority renamed to --stream-types and now excludes
   any stream types not specified.
 - Added --stream-sorting-excludes which excludes streams
   from the internal sorting used by best/worst synonyms.
 - Now returns exit code 1 on errors.

API:
 - plugin.get_streams(): Renamed priority parameter to stream_types
   and changed behaviour slightly.
 - plugin.get_streams(): Added the parameter sorting_excludes.

Plugins:
 - Added plugin for Aliez.tv.
 - Added plugin for Weeb.tv.
 - Added plugin for Veetle.
 - Added plugin for Euronews.
 - Dailymotion: Updated for JSON result changes.
 - Livestream: Added SWF verification.
 - Stream: Added httpstream://.
 - Stream: Now evaluates parameters as Python values.
 - Twitch/Justin.tv: Fixed HLS stream names.
 - Youtube Live: Improved stream names.


Version 1.4.5 (2013-05-11)
--------------------------

Plugins:
 - Twitch/Justin.tv: Fixed mobile transcode request never happening.
 - GOMTV.net: Fixed issue causing disabled streams to be picked up.
 - Azubu.tv: Updated for HTML change.

Streams:
 - HLS: Fixed potential crash when getting a invalid playlist.


Version 1.4.4 (2013-05-03)
--------------------------

Plugins:
 - Twitch/Justin.tv: Fixed possible crash on Python 3.
 - Ilive.to: HTML parsing fixes by Sam Edwards.


Version 1.4.3 (2013-05-01)
--------------------------

CLI:
 - Major refactoring of the code base.
 - Now respects the XDG Base Directory Specification.
   Will attempt to load config and plugins from the following paths:
    - $XDG_CONFIG_HOME/livestreamer/config
    - $XDG_CONFIG_HOME/livestreamer/plugins/
 - The option --quiet-player is now deprecated since
   it is now the default behaviour. A new option --verbose-player
   was added to show the player's console output.
 - The option --cmdline now prints arguments in quotes.
 - Print error message if the player fails to start.

Plugins:
 - Added a cache plugins can use to store data
   that does not need to be generated on every run.
 - Added Azubu.tv plugin.
 - Added owncast.me plugin by Athanasios Oikonomou.
 - Youtube: Updated for HTML changes.
 - GOMTV.net:
    - Fixed incorrect cookie names
    - Stream names are now more consistent
    - Added support for Limelight streams
 - Twitch/Justin.tv:
    - Fixed SWF verification issues
    - The HLS streams available are now higher quality

Streams:
 - Minor improvements and fixes to HDS.

Bug fixes:
 - Properly fixed named pipe support on Windows.


Version 1.4.2 (2013-03-01)
--------------------------

CLI:
 - Attempt to find VLC locations on OS X and Windows.
 - Added --stream-priority parameter.
 - Added --json parameter which makes livestreamer output JSON,
   useful for scripting in other languages.
 - Handle player exit cleaner by using SIGPIPE.

Plugins:
 - UStream: Now falls back on alternative CDNs when neccessary and added
   support for embed URLs.
 - Added ilive.to plugin by Athanasios Oikonomou.
 - Added cast3d.tv plugin by Athanasios Oikonomou.
 - streamingvideoprovider.co.uk: Added support for RTMP streams.
 - GOMTV.net: Major refactoring and also added support Adobe HDS streams.
 - SVTPlay: Added support for Adobe HDS streams.
 - Twitch/Justin.tv: Some minor tweaks and fixes.
 - Ongamenet: Update to URL and HTML changes.
 - Livestream.com: Update for HTML changes.

Streams:
 - Minor improvements and fixes to HLS.
 - Added support for Adobe HDS streams.

General:
 - Removed cache parameter from default player, since they do not work
   on older versions of VLC.
 - Added meta-stream "worst".
 - Removed sh dependancy and embeded pbs instead.

Bug fixes:
 - Fix named pipes on Windows x64.

API:
 - Added optional priority argument to Plugin.get_streams.
 - Improved docstrings.


Version 1.4.1 (2012-12-20)
--------------------------

CLI:
 - Added --ringbuffer-size option.

Plugins:
 - Fixed problem with UStream plugin and latest RTMPDump.
 - Added freedocast.com plugin by Athanasios Oikonomou.
 - Added livestation.com plugin by Athanasios Oikonomou.
 - Added mips.tv plugin by Athanasios Oikonomou.
 - Added streamingvideoprovider.co.uk plugin by Athanasios Oikonomou.
 - Added stream plugin that handles URLs such as hls://, rtmp://, etc.
 - Added yycast.com plugin by Athanasios Oikonomou.

Streams:
 - Refactored the HLS stream support.

General:
 - Bumped requests version requirement to 1.0.
 - Bumped sh version requirement to 1.07.


Version 1.4 (2012-11-23)
------------------------

CLI:
 - Added --rtmpdump-proxy option.
 - Added --plugin-dirs option.
 - Now automatically attempts to use secondary stream CDNs when primary fails.

Plugins:
 - Added Dailymotion plugin by Gaspard Jankowiak.
 - Added livestream.com plugin.
 - Added VOD support to GOMTV plugin.
 - Twitch plugin now finds HLS streams.
 - own3D.tv plugin now finds more CDNs.
 - Fixed bugs in Youtube and GOMTV plugin.
 - Refactored UStream plugin.

Streams:
 - Added support for AkamaiHD HTTP streams.

General:
 - Added unit tests, still fairly small coverage though.
 - Added travis-ci integration.
 - Now using python-sh on *nix since python-pbs is deprecated.
