Version 1.6.1
-------------

    Bug fixes:
     - CLI: Fixed broken ``--player-http`` and ``--player-continuous-http`` on Windows.
     - CLI: Fixed un-quoted player paths containing backslashes being broken.


Version 1.6.0
-------------

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


Version 1.5.2
-------------

    Plugins:
     - Twitch/Justin.tv: Fix stream names.


Version 1.5.1
-------------

    Plugins:
     - Added plugin for Filmon.
     - Twitch/Justin.tv: Safer cookie and SWF URL handling.
     - Youtube: Enable VOD support.

    Bug fixes:
     - Fixed potential crash when invalid UTF-8 is passed as arguments
       to subprocesses.


Version 1.5.0
-------------

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


Version 1.4.5
-------------

    Plugins:
     - Twitch/Justin.tv: Fixed mobile transcode request never happening.
     - GOMTV.net: Fixed issue causing disabled streams to be picked up.
     - Azubu.tv: Updated for HTML change.

    Streams:
     - HLS: Fixed potential crash when getting a invalid playlist.


Version 1.4.4
-------------

    Plugins:
     - Twitch/Justin.tv: Fixed possible crash on Python 3.
     - Ilive.to: HTML parsing fixes by Sam Edwards.


Version 1.4.3
-------------

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


Version 1.4.2
-------------

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


Version 1.4.1
-------------

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


Version 1.4
-----------

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

