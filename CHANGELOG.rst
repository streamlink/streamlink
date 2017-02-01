streamlink 0.3.0 (2017-01-24)
-------------------------------

Release 0.3.0 of Streamlink!

A lot of updates to each plugin (thank you @beardypig !), automated Windows releases, PEP8 formatting throughout Streamlink are some of the few updates to this release as we near a stable 1.0.0 release. 

Main features are:
  - Lot's of maintaining / updates to plugins
  - General bug and doc fixes
  - Major improvements to development (github issue templates, automatically created releases)

::

    Agustín Carrasco <asermax@gmail.com> (1):
          Links on crunchy's rss no longer contain the show name in the url (#379)
    
    Brainzyy <Brainzyy@users.noreply.github.com> (1):
          Add basic tests for stream.me plugin (#391)
    
    Javier Cantero <jcantero@escomposlinux.org> (2):
          plugins/twitch: use version v3 of the API
          plugins/twitch: use kraken URL
    
    John Smith <v2.0@protonmail.com> (3):
          Added support for bongacams.com streams (#329)
          streamlink_cli.main: close stream_fd on exit (#427)
          streamlink_cli.utils.progress: write new line at finish (#442)
    
    Max Riegler <rinukkusu@sub-r.de> (1):
          plugins.chaturbate: new regex (#457)
    
    Michiel Sikma <michiel@wedemandhtml.com> (1):
          Update PLAYER_VERSION, as old one does not return data. Add ability to use streams with /embed/video in the URL, from embedded players. (#311)
    
    Mohamed El Morabity <melmorabity@users.noreply.github.com> (6):
          Add support for pluzz.francetv.fr (#343)
          Fix ArteTV plugin (#385)
          Add support for Canal+ TV group channels (#416)
          Update installation instructions for Fedora (#443)
          Add support for Play TV (#439)
          Use token generator for HLS streams, as for HDS ones (#466)
    
    RosadinTV <rosadintv@outlook.com> (1):
          --can-handle-url-no-redirect parameter added (#333)
    
    Stefan Hanreich <stefanhani@gmail.com> (1):
          added chocolatey to the documentation (#380)
    
    bastimeyer <mail@bastimeyer.de> (3):
          Automatically create Github releases
          Set changelog in automated github releases
          Add a github issue template
    
    beardypig <beardypig@users.noreply.github.com> (55):
          plugins.tvcatchup: site layout changed, updated the stream regex to accommodate the change (#338)
          plugins.streamlive: streamlive.to have added some extra protection to their streams which currently prevents us from capturing them (#339)
          cli: add command line option to specific logging path for subprocess errorlog
          plugins.trtspor: added support for trtspor.com (#349)
          plugins.kanal7: fixed page change in kanal7 live stream (#348)
          plugins.picarto: Remove the unreliable rtmp stream (#353)
          packaging: removed the built in backports infavour of including them as dependencies when required (#355)
          Boost the test coverage a bit (#362)
          plugins: all regex string should be raw (#361)
          ci: build and test on Python 3.6 (+3.7 on travis, with allowed failure) (#360)
          packages.flashmedia: fix bug in AMFMessage (#359)
          tests: use mock from unittest when available otherwise fallback to mock (#358)
          stream.hls: try to retry stream segments (#357)
          tests: add codecov config file (#363)
          plugins.picarto: updated plugin to use tech_switch divs to find the stream parameters
          plugins.mitele: support for live streams on mitele.es
          docs: add a note about python-devel needing to be installed in some cases
          docs/release: generate the changelog as rst instead of md
          plugins.adultswim: support https urls
          use iso 8601 date format for the changelog
          plugins.tf1: added plugin to support tf1.fr and lci.fr
          plugins.raiplay: added plugin to support raiplay.it
          plugins.vaughnlive: updated player version and info URL (#383)
          plugins.tv8cat: added support for tv8.cat live stream (#390)
          Fix TF1.fr plugin (#389)
          plugins.stream: fix a default scheme handling for urls
          Add support for some Bulgarian live streams (#392)
          rtmp: fix bug in redirect for rtmp streams
          plugins.sportal: added support for the live stream on sportal.bg
          plugins.bnt: update the user agent string for the http requests
          plugins.ssh101: update to support new site layout
          Optionally use FFMPEG to mux separate video and audio streams (#224)
          Support for 4K videos in YouTube (#225)
          windows-installer: add the version info to the installer file
          include CHANGELOG.rst instead of .md in the egg
          stream.hls: output duplicate streams for HLS when multiple streams of the same quality are available
          stream.ffmpegmux: fix support for avconv, avconv will be used if ffmpeg is not found
          Adultswin VOD support (#406)
          Move streamlink_cli.utils.named_pipe in to streamlink.utils
          plugins.rtve: update plugin to support new streaming method
          stream.hds: omit HDS streams that are protected by DRM
          Adultswin VOD fix for live show replays (#418)
          plugins.rtve: add support for legacy stream URLs
          installer: remove the streamlink bin dir from %PATH% before installing
          plugins.twitch: only check hosted channels when playing a live stream
          docs: tweaks to docs and docs build process
          Fix iframe detection for BTN/cdn.bg streams (#437)
          fix some regex that give deprecation warnings in python 3.6
          plugins.adultswim: correct behaviour for archived streams
          plugins.nineanime: add scheme to grabber api url if not present
          session: add an option to disable Diffie Hellman key exchange
          plugins.srgssr: added support for srg ssr sites: srf, rts and rsi
          plugins.srgssr: fixed bug in api URL and fixed akamai urls with authparams
          cli: try to terminate the player process before killing it (if terminate takes too long)
          plugins.swisstxt: add support for the SRG SSR sites sports sections
    
    fozzy <fozzysec@gmail.com> (1):
          Add plugin for huajiao.com and zhanqi.tv (#334)
    
    sqrt2 <sqrt2@users.noreply.github.com> (1):
          Fix swf_url in livestream.com plugin (#428)
    
    stepshal <nessento@openmailbox.org> (1):
          Remove trailing.
    
    stepshal <stepshal@users.noreply.github.com> (2):
          Add blank line after class or function definition (#408)
          PEP8 (#414)
    

streamlink 0.2.0 (2016-12-16)
-----------------------------

Release 0.2.0 of Streamlink!

We've done numerous changes to plugins as well as fixed quite a few
which were originally failing. Among these changes are updated docs as
well as general UI/UX cleaning with console output.

The main features are: - Additional plugins added - Plugin fixes -
Cleaned up console output - Additional documentation (contribution,
installation instructions)

Again, thank you everyone whom contributed to this release! :D

::

    Beardypig <beardypig@users.noreply.github.com> (6):
          Turkish Streams Part III (#292)
          coverage: include streamlink_cli in the coverage, but exclude the vendored packages (#302)
          Windows command line parsing fix (#300)
          plugins.atresplayer: add support for live streams on atresplayer.com (#303)
          Turkish Streams IV (#305)
          Support for local files (#304)

    Charlie Drage <charlie@charliedrage.com> (2):
          Spelling error in release script
          Fix issue with building installer

    Fishscene <fishscene@gmail.com> (3):
          Updated homepage
          Updated README.md
          Fixed type in README.md.

    Forrest <gravyboat@users.noreply.github.com> (3):
          Modify the browser redirect (#191)
          Update client ID (#241)
          Update requests version after bug fix (#239)

    Josip Ponjavic <josipponjavic@gmail.com> (1):
          Add NixOS install instructions

    Simon Bernier St-Pierre <sbernierstpierre@gmail.com> (1):
          add contributing guidelines

    bastimeyer <mail@bastimeyer.de> (1):
          Add metadata to Windows installer

    beardypig <beardypig@users.noreply.github.com> (25):
          plugins.nhkworld: update the plugin to use the new HLS streams
          plugins.picarto: updated the plugin to use the new javascript and support HLS streams
          add pycryptodome==3.4.3 to the setup.py dependencies
          plugins.nineanime: added a plugin to support 9anime.to
          plugins.nineanime: update the plugin matrix in the docs
          plugins.atv: add support for the live stream on atv.com.tr
          include omxplayer in the list of players in the documentation
          update the player docs with findings from @Junior1544 and @stevekmcc
          plugins.bigo: support for bigo.tv
          docs: move pycryptodome to the list of automatically installed libraries in the docs
          plugins.dingittv: add support for dingit.tv
          plugins.crunchyroll: support ultra quality for subscribers
          update URL for docs to point to the github.io page
          stream.hls: stream the HLS segments out to the player as they are downloaded, decrypting on the fly
          installer: install the required MS VC++ runtime files beside the python installation (see takluyver/pynsist/pull/87)
          plugins.bigo: FlashVars regex updated due to site change
          add some license notices for the bundled libraries
          plugins.youtube: support additional live urls
          add support for a few Turkish live streams
          plugins.foxtr: add support for turkish fox live streams
          plugins.kralmuzik: basic support for the HLS stream only
          stream.hds: added option to force akamai authentication plugins.startv: refactored in to a base class, to be used in other plugins that use the same hosting as StarTV plugins.kralmuzik: refactored to use StarTVBase plugins.ntv: added NTV support
          plugins.atv: add support for a2tv which is very similar to atv
          plugins.dogan: support for teve2, kanald, dreamtv, and ccnturk via the same plugin
          plugins.trt: added support for the live channels on trt.net.tr

    che <che27012011@googlemail.com> (1):
          plugins.twitch: support for clips added

    ioblank <iosonoblank@gmail.com> (1):
          Use ConsoleOutput for run-as-root warning

    mmetak <mmetak@users.noreply.github.com> (3):
          Update install instruction (#257)
          Add links for windows portable version. (#299)
          Add package maintainers to docs. (#301)

    thatlinuxfur <toss1@zootboy.com> (1):
          Added tigerdile.com support. (#221)

streamlink 0.1.0 (2016-11-21)
-----------------------------

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

::

    Beardypig <beardypig@users.noreply.github.com> (13):
          fix stream quality naming issue with py2 vs. py3, fixing #89 (#96)
          updated connectcast plugin to support the new rtmp streams; fixes #93 (#95)
          Fix for erroneous escape coding the livecoding plugin. Fixes #106 (#121)
          TVPlayer.com: fix for 400 error, correctly set the platform parameter (#123)
          Added a method to automatically determine the encoding when parsing JSON, if no encoding is provided. (#122)
          when retry-streams and twitch-disable-hosting arguments are used the stream is retried until a non-hosted stream is found (#125)
          plugins.goodgame: Update for API change (#130)
          plugins.adultswim: added a new adultswim.com plugin (#139)
          plugins.goodgame: restored DDOS protection cookie support (#136)
          plugins.younow: update API url (#135)
          plugins.euronew: update to support the new site (#141)
          plugins.webtv: added a new plugin to support web.tv (#144)
          plugins.connectcast: fix regex issue with python 3 (#152)

    Brainzyy <Brainzyy@users.noreply.github.com> (1):
          Add piczel.tv plugin (courtesy of @intact) (#114)

    Charlie Drage <charlie@charliedrage.com> (1):
          Update release scripts

    Erk- <Erk-@users.noreply.github.com> (1):
          Changed the twitch plugin to use https instead of http as discussed in #103 (#104)

    Forrest <gravyboat@users.noreply.github.com> (2):
          Modify the changelog link (#107)
          Update cli to note a few windows issues (#108)

    Simon Bernier St-Pierre <sbernierstpierre@gmail.com> (1):
          change icon

    Simon Bernier St-Pierre <sbstp@users.noreply.github.com> (1):
          finish the installer (#98)

    Stefan <stefan-github@yrden.de> (1):
          Debian packaging base (#80)

    Stefan <stefanhani@gmail.com> (1):
          remove run-as-root option, reworded warning #85 (#109)

    Weslly <weslly.honorato@gmail.com> (1):
          Fixed afreecatv.com url matching (#90)

    bastimeyer <mail@bastimeyer.de> (2):
          Improve NSIS installer script
          Remove shortcut from previous releases on Windows

    beardypig <beardypig@users.noreply.github.com> (8):
          plugins.cybergame: update to support changes to the live streams on the cybergame.tv website
          Use pycryptodome inplace of pyCrypto
          Automated build of the Windows NSIS installer
          support for relative paths for rtmpdump
          makeinstaller: install the streamlinkrc file in to the users %APPDATA% directory
          remove references to livestreamer in the win32 config template
          stream.rtmpdump: fixed the rtmpdump path issue, introduced in 6bf7fd7
          pin requests to <2.12.0 to avoid the strict IDNA2008 validation

    ethanhlc <ethanhlc@users.noreply.github.com> (1):
          fixed instance of livestreamer (#99)

    intact <intact.devel@gmail.com> (1):
          plugins.livestream: Support old player urls

    mmetak <mmetak@users.noreply.github.com> (2):
          fix vaughnlive.tv info_url (#88)
          fix vaughnlive.tv info_url (yet again...) (#143)

    skulblakka <pascal.romahn@mailbox.org> (1):
          Overworked Plugin for ZDF Mediathek (#154)

    sqrt2 <sqrt2@users.noreply.github.com> (1):
          Fix ORF TVthek plugin (#113)

    tam1m <tam1m@users.noreply.github.com> (1):
          Fix zdf_mediathek TypeError (#156)

streamlink 0.0.2 (2016-10-12)
-----------------------------

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

As always, below is a ``git shortlog`` of all changes from the previous
release of Streamlink (0.0.1) to now (0.0.2).

::

    Brainzyy <Brainzyy@users.noreply.github.com> (1):
          add stream.me to the docs

    Charlie Drage <charlie@charliedrage.com> (9):
          Add script to generate authors list / update authors
          Add release script
          Get setup.py ready for a release.
          Revert "Latest fix to plugin from livestreamer"
          0.0.1 Release
          Update the README with installation notes
          Update copyright author
          Update plugin description on README
          It's now 2016

    Forrest <gravyboat@users.noreply.github.com> (1):
          Add a coverage file (#54)

    Forrest Alvarez <forrest.alvarez@gmail.com> (4):
          Modify release for streamlink
          Remove faraday from travis run
          Remove tox
          Add the code coverage badge

    Latent Logic <lat.logic@gmail.com> (1):
          Picarto plugin: multistream workaround (fixes #50)

    Maschmi <Maschmi@users.noreply.github.com> (1):
          added travis build status badge fixes #74 (#76)

    Randy Taylor <tehgecKozzz@gmail.com> (1):
          Fix typo in issues docs and improve wording (#61)

    Simon Bernier St-Pierre <sbernierstpierre@gmail.com> (8):
          add script to build & copy the docs
          move makedocs.sh to script/
          Automated docs updates via travis-ci
          prevent the build from hanging
          fix automated commit message
          add streamboat to the docs
          disable docs on pull requests
          twitch.tv: add option to disable hosting

    Simon Bernier St-Pierre <sbstp@users.noreply.github.com> (2):
          Don't delete everything if docs build fail (#62)
          Create install script for pynsist (#27)

    beardypig <beardypig@users.noreply.github.com> (3):
          TVPlayer plugin supports the latest version of the website
          crunchyroll: decide if to parse the stream links as HLS variant playlist or plain old HLS stream (fixes #70)
          itvplayer: updated the productionId extraction method

    boda2004 <boda2004@gmail.com> (1):
          fixed periscope live streaming and allowed url re (#79)

    ethanhlc <sakithree@gmail.com> (1):
          fixed instances of chrippa/streamlink to streamlink/streamlink

    scottbernstein <scott_bernstein@hotmail.com> (1):
          Latest fix to plugin from livestreamer

    steven7851 <steven7851@msn.com> (1):
          Update plugin.douyutv

streamlink 0.0.1 (2016-09-23)
-----------------------------

The first release of Streamlink!

This is the first release from the initial fork of Livestreamer. We aim
to have a concise, fast review process and progress in terms of
development and future releases.

Below is a ``git shortlog`` of all commits since the last change within
Livestream (hash ab80dbd6560f6f9835865b2fc9f9c6015aee5658). This will
serve as a base-point as we continue development of "Streamlink".

New releases will include a list of changes as we add new features /
code refactors to the existing code-base.

::

    Agustin Carrasco <asermax@gmail.com> (2):
          plugins.crunchyroll: added support for locale selection
          plugins.crunchyroll: use locale parameter on the header's user-agent as well

    Alan Love <alan@cattes.us> (3):
          added support for livecoding.tv
          removed printing
          updated plugin matrix

    Alexander <AleXoundOS@users.noreply.github.com> (1):
          channel info url change in afreeca plugin

    Andreas Streichardt <andreas.streichardt@gmail.com> (1):
          Add Sportschau

    Anton <anton9121@gmail.com> (2):
          goodgame ddos validation
          add stream_id with words

    Benedikt Gollatz <ben@differentialschokolade.org> (1):
          Add support for ORF TVthek livestreams and VOD segments

    Benoit Dien <benoit.dien@gmail.com> (1):
          Meerkat plugin

    Brainzyy <Brainzyy@users.noreply.github.com> (1):
          fix azubu.tv plugin

    Charlie Drage <charlie@charliedrage.com> (9):
          Update the README
          Fix travis
          Rename instances of "livestreamer" to "streamlink"
          Fix travis
          Add script to generate authors list / update authors
          Get setup.py ready for a release.
          Add release script
          Revert "Latest fix to plugin from livestreamer"
          0.0.0 Release

    Charmander <~@charmander.me> (1):
          plugins.picarto: Update for API and URL change

    Chris-Werner Reimer <creimer@betaworx.eu> (1):
          fix vaughnlive plugin #897

    Christopher Rosell <chrippa@tanuki.se> (7):
          plugins.twitch: Handle subdomains with dash in them, e.g. en-gb.
          cli: Close output on exit.
          Show a brief usage when no option is specified.
          cli: Fix typo.
          travis: Use new artifacts tool.
          docs: Fix readthedocs build.
          travis: Build installer exe aswell.

    Daniel Meißner <daniel@3st.be> (2):
          plugin: added media_ccc_de api and protocol changes
          docs/plugin_matrix: removed needless characters

    Dominik Sokal <dominiksokal@gmail.com> (1):
          plugins.afreeca: fix stream

    Ed Holohan <edmund@holohan.us> (1):
          Quick hack to handle Picarto changes

    Emil Stahl <emil@emilstahl.dk> (1):
          Add support for viafree.dk

    Erik G <aposymbiosis@gmail.com> (7):
          Added plugin for Dplay.
          Added plugin for Dplay and removed sbsdiscovery plugin.
          Add HLS support, adjust API schema, no SSL verify
          Add pvswf parameter to HDS stream parser
          Fix Video ID matching, add .no & .dk support, add error handling
          Match new URL, add HDS support, handle incorrect geolocation
          Add API support

    Fat Deer <fatdeer@foxmail.com> (1):
          Update pandatv.py

    Forrest Alvarez <forrest.alvarez@gmail.com> (3):
          Add some python releases
          Add coveralls to after_success
          Remove artifacts

    Guillaume Depardon <guillaume.depardon@outlook.com> (1):
          Now catching socket errors on send

    Javier Cantero <jcantero@escomposlinux.org> (1):
          Add new parameter to Twitch usher URL

    Jeremy Symon <jtsymon@gmail.com> (2):
          Sort list of streams by quality
          Avoid sorting streams twice

    Jon Bergli Heier <snakebite@jvnv.net> (2):
          plugins.nrk: Updated for webpage changes.
          plugins.nrk: Fixed _id_re regex not matching series URLs.

    Kari Hänninen <lonefox@kapsi.fi> (7):
          Use client ID for twitch.tv API calls
          Revert "update INFO_URL for VaughnLive"
          Remove spurious print statement that made the plugin incompatible with python 3.
          livecoding.tv: fix breakage ("TypeError: cannot use a string pattern on a bytes-like object")
          sportschau: Fix breakage ("TypeError: a bytes-like object is required, not 'str'"). Also remove debug output.
          Update the plugin matrix
          Bump version to 1.14.0-rc1

    Marcus Soll <Superschlumpf@web.de> (2):
          Added plugin for blip.tv VOD
          Updated blip.tv plugin

    Mateusz Starzak <mstarzak@gmail.com> (1):
          Update periscope.py

    Michael Copland <mjbcopland@gmail.com> (1):
          Fixed weighting of Twitch stream names

    Michael Hoang <enzime@users.noreply.github.com> (1):
          Add OPENREC.tv plugin and chmod 2 files

    Michiel <msvos@liacs.nl> (1):
          Support for Tour de France stream

    Paul LaMendola <paulguy119@gmail.com> (2):
          Maybe fixed ustream validation failure.
          More strict test for weird stream.

    Pavlos Touboulidis <pav@pav.gr> (2):
          Add antenna.gr plugin
          Update plugin matrix for antenna

    Robin Schroer <sulami@peerwire.org> (1):
          azubutv: set video_player to None if stream is offline

    Seth Creech <sethaaroncreech@gmail.com> (1):
          Added logic to support host mode

    Simon Bernier St-Pierre <sbernierstpierre@gmail.com> (5):
          update the streamup.com plugin
          support virtualenv
          update references to livestreamer
          add stream.me plugin
          add streamboat plugin

    Summon528 <cody880528@hotmail.com> (1):
          add support to afreecatv.com.tw

    Swirt <swirt.ac@gmail.com> (2):
          Picarto plugin: update RTMPStream-settings
          Picarto plugin: update RTMPStream-settings

    Tang <sugar1987cn@gmail.com> (1):
          New provider: live.bilibili.com

    Warnar Boekkooi <warnar@boekkooi.net> (1):
          NPO token fix

    WeinerRinkler <drachenlord@8chan.co> (2):
          First version
          Error fixed when streamer offline or invalid

    blxd <blxd@users.noreply.github.com> (5):
          fixed tvcatchup.com plugin, the website layout changed and the method to find the stream URLs needed to be updated.
          tvcatchup now returns a variant playlist
          tvplayer.com only works with a browser user agent
          not all channels return hlsvariant playlists
          add user agent header to the tvcatchup plugin

    chvrn <chev@protonmail.com> (4):
          added expressen plugin
          added expressen plugin
          update() => assign with subscript
          added entry for expressen

    e00E <vakevk+git@gmail.com> (1):
          Fix Twitch plugin not working because bandwith was parsed as an int when it is really a float

    fat deer <fatdeer@foxmail.com> (1):
          Add Panda.tv Plugin.

    fcicq <fcicq@fcicq.net> (1):
          add afreecatv.jp support

    hannespetur <hannespetur@gmail.com> (8):
          plugin for Ruv - the Icelandic national television - was added
          removed print statements and started to use quality key as audio if the url extensions is mp3
          the plugin added to the plugin matrix
          removed unused import
          alphabetical order is hard
          removed redundant assignments of best/worst quality
          HLS support added for the Ruv plugin
          Ruv plugin: returning generators instead of a dict

    int3l <int3l@users.noreply.github.com> (1):
          Refactoring and update for the VOD support

    intact <intact.devel@gmail.com> (21):
          plugins.artetv: Update json regex
          Updated douyutv.com plugin
          Added plugin for streamup.com
          plugins.streamupcom: Check live status
          plugins.streamupcom: Update for API change
          plugins.streamupcom: Update for API change
          plugins.dailymotion: Add HLS streams support
          plugins.npo: Fix Python 3 compatibility
          plugins.livestream: Prefer standard SWF players
          plugins.tga: Support more streams
          plugins.tga: Fix offline streams
          plugins.vaughnlive: Fix INFO_URL
          Added plugin for vidio.com
          plugins.vaughnlive: Update for API change
          plugins.vaughnlive: Fix app for some ingest servers
          plugins.vaughnlive: Remove debug print
          plugins.vaughnlive: Lowercase channel name
          plugins.vaughnlive: Update for API change
          plugins.vaughnlive: Update for API change
          plugins.livestream: Tolerate missing swf player URL
          plugins.livestream: Fix player URL

    jkieberk <jkieberking@gmail.com> (1):
          Change Fedora Package Manager from Yum  to Dnf

    kviktor <kviktor@cloud.bme.hu> (2):
          plugins: mediaklikk.hu stream and video support
          update mediaklikk plugin

    livescope <livescope@users.noreply.github.com> (1):
          Add VOD/replay support for periscope.tv

    liz1rgin <waiphereme@gmail.com> (2):
          Fix goodgame find Streame
          Update goodgame.py

    maop <me@marcoalfonso.net> (1):
          Add Beam.pro plugin.

    mindhalt <mindhalt@gmail.com> (1):
          Update redirect URI after successful twitch auth

    neutric <ah0703@googlemail.com> (1):
          Update issues.rst

    nitpicker <daniel@localhost> (2):
          I doesn't sign the term of services, so I doesnt violate!
          update INFO_URL for VaughnLive

    oyvindln <mail@example.com> (1):
          Allow https urls for nrk.no.

    ph0o <ph0o@users.noreply.github.com> (1):
          Create servustv.py

    pulviscriptor <pulviscriptor@gmail.com> (1):
          GoodGame URL parse fix

    scottbernstein <scott_bernstein@hotmail.com> (1):
          Latest fix to plugin from livestreamer

    steven7851 <steven7851@msn.com> (16):
          plugins.douyutv: Use new api.
          update douyu
          fix cdn..
          fix for Python 3.x..
          use mobile api for reducing code
          fix for non number channel
          add middle and low quality
          fix quality
          fix room id regex
          make did by UUID module
          fix channel on event
          more retries for redirection
          remove useless lib
          try to support event page
          use https protocol
          Update plugin.douyutv

    trocknet <trocknet@github> (1):
          plugins.afreeca: Fix HLS stream.

    whizzoo <grenardus@gmail.com> (2):
          Add RTLXL plugin
          Add RTLXL plugin

    wolftankk <wolftankk@gmail.com> (3):
          get azubu live status from api
          use new api get stream info
          fix video_player error
