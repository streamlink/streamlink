# Changelog

This document only contains changelogs for releases of the current major version. Please see [Streamlink's documentation](https://streamlink.github.io/changelog/index.html) for changelogs of old major version releases, or check the `docs/changelog` directory of [Streamlink's git repository](https://github.com/streamlink/streamlink/tree/master/docs/changelog).

## streamlink 8.6.3 (2026-10-29)

- SECURITY: new minor release primarily for Streamlink's Windows / Linux AppImages builds, with `brotli 1.2.1` (via uv.lock) ([`CVE-2026-111497`](https://nvd.nist.gov/vuln/detail/CVE-2026-111497))
- Fixed: `--retry-streams` and `--retry-max` in external/continuous HTTP output mode when re-fetching ([#7165](https://github.com/streamlink/streamlink/pull/7165))
- Build: bumped `pycryptodome` version requirements to `>=3.4.3,<5` ([#7167](https://github.com/streamlink/streamlink/pull/7167))
- Tests: fixed race-conditions in HLS tests ([#7174](https://github.com/streamlink/streamlink/pull/7174), [#7176](https://github.com/streamlink/streamlink/pull/7176))

[Full changelog](https://github.com/streamlink/streamlink/compare/8.6.2...8.6.3)


## streamlink 8.6.2 (2026-10-07)

- SECURITY: fixed arbitrary local file read via `file://` URLs in DASH `Location` tags (`CVE-2026-TO-BE-ASSIGNED` / [`GHSA-j7pf-m7gx-jr33`](https://github.com/streamlink/streamlink/security/advisories/GHSA-j7pf-m7gx-jr33)) ([`98781761`](https://github.com/streamlink/streamlink/commit/987817618f57b6def852693e4e0a95fd9c8437f2))
- Changed: `validate.xml_xpath()` and `validate.xml_xpath_string()` to include access to `re:test()`, `re:match()` and `re:replace()` regex functions ([#7151](https://github.com/streamlink/streamlink/pull/7151))
- Changed: log format of deprecation warnings ([#7141](https://github.com/streamlink/streamlink/pull/7141))
- Fixed: missing deprecation warnings for already deprecated CLI arguments (req. Python 3.13+) ([#7141](https://github.com/streamlink/streamlink/pull/7141))
- Fixed: being able to close `SegmentedStreamReader` streams without opening them first, emitting log records on garbage collection ([#7146](https://github.com/streamlink/streamlink/pull/7146))
- Updated plugins:
  - blazetv: fixed live streams ([#7147](https://github.com/streamlink/streamlink/pull/7147))
  - cinergroup: fixed Bloomberg HT ([#7132](https://github.com/streamlink/streamlink/pull/7132))
  - dogan: fixed plugin ([#7138](https://github.com/streamlink/streamlink/pull/7138))
  - facebook: re-introduced plugin with new implementation ([#7115](https://github.com/streamlink/streamlink/pull/7115))
  - vimeo: rewritten and fixed plugin ([#7069](https://github.com/streamlink/streamlink/pull/7069))
  - youtvua: added new plugin ([#7140](https://github.com/streamlink/streamlink/pull/7140))
- Docs: tightened rules about AI-assisted contributions and security vulnerability reports ([#7136](https://github.com/streamlink/streamlink/pull/7136), [#7152](https://github.com/streamlink/streamlink/pull/7152))

[Full changelog](https://github.com/streamlink/streamlink/compare/8.6.1...8.6.2)


## streamlink 8.6.1 (2026-09-16)

- Fixed: compatibility with urllib3 2.8.0 ([#7117](https://github.com/streamlink/streamlink/pull/7117))

[Full changelog](https://github.com/streamlink/streamlink/compare/8.6.0...8.6.1)


## streamlink 8.6.0 (2026-09-13)

- SECURITY: fixed arbitrary local file read via HTTP(S) redirection to `file://` URL ([`CVE-2026-92164`](https://nvd.nist.gov/vuln/detail/CVE-2026-92164) / [`GHSA-vf2x-4v53-pm7v`](https://github.com/streamlink/streamlink/security/advisories/GHSA-vf2x-4v53-pm7v)) ([`4b99c64d`](https://github.com/streamlink/streamlink/commit/4b99c64dde21ea70c24d9ffdbd15849b05f465c6))
- SECURITY: fixed insecure cross-scheme redirection (HTTPS -> HTTP) ([`CVE-2026-92164`](https://nvd.nist.gov/vuln/detail/CVE-2026-92164) / [`GHSA-vf2x-4v53-pm7v`](https://github.com/streamlink/streamlink/security/advisories/GHSA-vf2x-4v53-pm7v)) ([`4b99c64d`](https://github.com/streamlink/streamlink/commit/4b99c64dde21ea70c24d9ffdbd15849b05f465c6))
- Added: official support for Python 3.15 ([#7026](https://github.com/streamlink/streamlink/pull/7026))
- Added: support for HLS packed audio streams ([#7083](https://github.com/streamlink/streamlink/pull/7083), [#7082](https://github.com/streamlink/streamlink/pull/7082))
- Added: `HLSSegment.{get,iter}_content()` and `HLSStreamWriter.{get,iter}_segment_content()` for being able to modify segment data ([#7059](https://github.com/streamlink/streamlink/pull/7059))
- Added: `itsoffset` option to `FFMPEGMuxer` ([#7081](https://github.com/streamlink/streamlink/pull/7081))
- Added: `nextjs_inline_rsc()` to `validate` API ([#7110](https://github.com/streamlink/streamlink/pull/7110))
- Fixed: HTTP server of `--player-http`/`--player-continuous-http` binding to all interfaces ([#7051](https://github.com/streamlink/streamlink/pull/7051))
- Fixed: zero or negative duration values in HLS dateranges ([#7074](https://github.com/streamlink/streamlink/pull/7074))
- Fixed: incorrect `t` attribute evaluation in DASH `SegmentTimeline.S` nodes ([#7075](https://github.com/streamlink/streamlink/pull/7075))
- Updated plugins:
  - ard_live: removed plugin ([#7091](https://github.com/streamlink/streamlink/pull/7091))
  - ard_mediathek: rewritten and fixed plugin ([#7090](https://github.com/streamlink/streamlink/pull/7090))
  - atresplayer: refactored stream retrieval ([#7062](https://github.com/streamlink/streamlink/pull/7062))
  - bigo: added MPEG-TS packet header decryption due to Bigo's web-protection ([#7056](https://github.com/streamlink/streamlink/pull/7056), [#7059](https://github.com/streamlink/streamlink/pull/7059))
  - bigo: worked around account requirements ([#7106](https://github.com/streamlink/streamlink/pull/7106), [#7109](https://github.com/streamlink/streamlink/pull/7109))
  - cdnbg: fixed player\_url schema ([#7036](https://github.com/streamlink/streamlink/pull/7036))
  - douyu: fixed API call failures on systems with unsynced clocks ([#7065](https://github.com/streamlink/streamlink/pull/7065))
  - filmon: updated URL matcher and switched to v2 APIs ([#7105](https://github.com/streamlink/streamlink/pull/7105))
  - goodgame: fixed stream retrieval ([#7086](https://github.com/streamlink/streamlink/pull/7086))
  - kick: fixed VODs ([#7108](https://github.com/streamlink/streamlink/pull/7108))
  - nimotv: fixed access to streams ([#7111](https://github.com/streamlink/streamlink/pull/7111))
  - okru: fixed metadata schema ([#7092](https://github.com/streamlink/streamlink/pull/7092))
  - piczel: removed plugin ([#7102](https://github.com/streamlink/streamlink/pull/7102))
  - pluto: fixed URL matcher, channel ID resolver and VODs ([#7048](https://github.com/streamlink/streamlink/pull/7048), [#7100](https://github.com/streamlink/streamlink/pull/7100))
  - tiktok: rewritten and fixed stream data schema for access to origin streams ([#7077](https://github.com/streamlink/streamlink/pull/7077))
  - twitch: added support for portrait-format streams ([#7087](https://github.com/streamlink/streamlink/pull/7087))
  - twitch: fixed missing category stream metadata breaking all stream metadata ([#7025](https://github.com/streamlink/streamlink/pull/7025))
  - vidio: rewritten and fixed plugin ([#7063](https://github.com/streamlink/streamlink/pull/7063))
  - zdf_mediathek: rewritten and fixed plugin ([#7093](https://github.com/streamlink/streamlink/pull/7093))
- Dependencies: bumped min. version requirement of lxml to `5.0.0` ([#7029](https://github.com/streamlink/streamlink/pull/7029))

[Full changelog](https://github.com/streamlink/streamlink/compare/8.5.0...8.6.0)


## streamlink 8.5.0 (2026-08-01)

- Fixed: named-pipe player inputs not being cleaned up on pre-open failure ([#6935](https://github.com/streamlink/streamlink/pull/6935))
- Fixed: stream start offsets being incorrectly cast to int in HLS ([#6941](https://github.com/streamlink/streamlink/pull/6941))
- Fixed: `hls-playlist-reload-time` not accepting floats ([#6957](https://github.com/streamlink/streamlink/pull/6957))
- Refactored: `HTTPSession` and fixed many typing issues ([#6924](https://github.com/streamlink/streamlink/pull/6924))
- Refactored: `MPDNode` in DASH manifest parser to allow attribute namespaces ([#6988](https://github.com/streamlink/streamlink/pull/6988))
- Updated plugins:
  - douyin: fixed validation schema ([#6930](https://github.com/streamlink/streamlink/pull/6930))
  - douyu: re-introduced plugin with new implementation ([#6959](https://github.com/streamlink/streamlink/pull/6959), [#7003](https://github.com/streamlink/streamlink/pull/7003))
  - mdstrm: added support for VODs / embedded streams with access tokens ([#6994](https://github.com/streamlink/streamlink/pull/6994))
  - nos: rewritten and fixed plugin ([#6954](https://github.com/streamlink/streamlink/pull/6954))
  - radiko: fixed live\_url value ([#6962](https://github.com/streamlink/streamlink/pull/6962))
  - trovo: removed plugin ([#6999](https://github.com/streamlink/streamlink/pull/6999))
  - tvazteca: added new plugin ([#6994](https://github.com/streamlink/streamlink/pull/6994))
- Docs: clarified requirements of Twitch high quality streams ([#6992](https://github.com/streamlink/streamlink/pull/6992))
- Tests: fixed test failures since Python 3.15 beta 1 ([#6919](https://github.com/streamlink/streamlink/pull/6919))
- Security: made GitHub releases immutable ([#6927](https://github.com/streamlink/streamlink/pull/6927))
- Security: pinned all GitHub actions to commit IDs ([#6936](https://github.com/streamlink/streamlink/pull/6936))
- Security: switched to uv lockfile for all CI workflows and for building release assets ([#6948](https://github.com/streamlink/streamlink/pull/6948))
- Misc: added pre-built FISH shell completions to release tarballs and wheels ([#7014](https://github.com/streamlink/streamlink/pull/7014))

[Full changelog](https://github.com/streamlink/streamlink/compare/8.4.0...8.5.0)


## streamlink 8.4.0 (2026-05-06)

- SECURITY: fixed arbitrary local file read via `file://` URI in HLS and DASH ([`CVE-2026-44353`](https://nvd.nist.gov/vuln/detail/CVE-2026-44353) / [`GHSA-hgqw-6m45-hw5f`](https://github.com/streamlink/streamlink/security/advisories/GHSA-hgqw-6m45-hw5f)) ([`ef56b4f8`](https://github.com/streamlink/streamlink/commit/ef56b4f8626afaf2ddbfb1ebe0cf471b9b7c47af), [`c9f3f0df`](https://github.com/streamlink/streamlink/commit/c9f3f0dfc8d80fca885b42a1436110bb07a5ddbe))
- Added: `--stream-passthrough-encrypted` for passing through encrypted HLS/DASH segments to the output stream without any checks ([#6896](https://github.com/streamlink/streamlink/pull/6896))
- Fixed: `--interface` selection by name on macOS ([#6908](https://github.com/streamlink/streamlink/pull/6908))
- Fixed: `--interface` not being applied to adapters mounted after session init ([#6915](https://github.com/streamlink/streamlink/pull/6915))
- Updated plugins:
  - goltelevision: rewritten and fixed plugin ([#6916](https://github.com/streamlink/streamlink/pull/6916))
  - twitcasting: improved ad segment filtering ([#6910](https://github.com/streamlink/streamlink/pull/6910))

[Full changelog](https://github.com/streamlink/streamlink/compare/8.3.0...8.4.0)


## streamlink 8.3.0 (2026-04-10)

- Added: support for choosing the `--interface` by name on non-Windows systems, with optional prefixes, similar to curl ([#6862](https://github.com/streamlink/streamlink/pull/6862))
- Added: support for also checking stream segments in `HLSStream.parse_variant_playlist()` by setting `check_streams="segments"` ([#6878](https://github.com/streamlink/streamlink/pull/6878))
- Fixed: stdout/stderr streams in `ProcessOutput` not being fully line-buffered ([#6868](https://github.com/streamlink/streamlink/pull/6868))
- Updated plugins:
  - cdnbg: rewritten and fixed plugin ([#6890](https://github.com/streamlink/streamlink/pull/6890))
  - nicolive: added websocket reconnect attempts on HLS decryption key retrieval failure ([#6871](https://github.com/streamlink/streamlink/pull/6871))
  - soop: migrated to sooplive.com ([#6876](https://github.com/streamlink/streamlink/pull/6876))
  - telefe: rewritten and fixed plugin ([#6891](https://github.com/streamlink/streamlink/pull/6891))

[Full changelog](https://github.com/streamlink/streamlink/compare/8.2.1...8.3.0)


## streamlink 8.2.1 (2026-03-05)

- Changed: HLS stream names using the "pixels" format to include framerate data, if available ([#6848](https://github.com/streamlink/streamlink/pull/6848))
- Deprecated: imports of re-exported attributes from `streamlink.stream` ([#6821](https://github.com/streamlink/streamlink/pull/6821))
- Fixed: plugin-related typing issues and missing typing annotations ([#6822](https://github.com/streamlink/streamlink/pull/6822))
- Updated plugins:
  - ceskatelevize: fixed sports streams ([#6826](https://github.com/streamlink/streamlink/pull/6826))
  - nrk: updated to tv-player v9 ([#6841](https://github.com/streamlink/streamlink/pull/6841))
  - pluto: updated to v2 API ([#6851](https://github.com/streamlink/streamlink/pull/6851))
  - twitch: switched to Usher v2 API endpoints ([#6840](https://github.com/streamlink/streamlink/pull/6840), [#6847](https://github.com/streamlink/streamlink/pull/6847))
  - youtube: updated API clientVersion ([#6853](https://github.com/streamlink/streamlink/pull/6853))

[Full changelog](https://github.com/streamlink/streamlink/compare/8.2.0...8.2.1)


## streamlink 8.2.0 (2026-02-09)

- Added: `--http-cookies-file` CLI argument and `http-cookies-files` session option ([#6796](https://github.com/streamlink/streamlink/pull/6796))
- Changed: `PluginError` to also be raised when setting a plugin's `url` attribute to a value that doesn't match any of its URL matchers, not just when initializing the plugin class ([#6810](https://github.com/streamlink/streamlink/pull/6810))
- Deprecated: imports of re-exported module attributes from `streamlink.utils` ([#6819](https://github.com/streamlink/streamlink/pull/6819))
- Fixed: `LogRecord` missing the function name and stack info ([#6788](https://github.com/streamlink/streamlink/pull/6788))
- Fixed: custom network interface being reset when disabling Diffie-Hellman key exchange ([#6795](https://github.com/streamlink/streamlink/pull/6795))
- Fixed: broken logic when unsetting ipv4/ipv6 session options ([#6795](https://github.com/streamlink/streamlink/pull/6795))
- Fixed: edge case when trying to detect the text encoding of certain kinds of HTML responses ([#6802](https://github.com/streamlink/streamlink/pull/6802))
- Fixed: missing representation not being handled when polling dynamic DASH manifests ([#6807](https://github.com/streamlink/streamlink/pull/6807))
- Updated plugins:
  - dailymotion: disabled TLS session tickets, fixing 403 HLS playlist responses on Python builds with an older version of OpenSSL ([#6816](https://github.com/streamlink/streamlink/pull/6816))
- Docs: bumped dependencies with support for Sphinx 9 ([#6783](https://github.com/streamlink/streamlink/pull/6783))
- Docs: added rules for AI-assisted contributions ([#6782](https://github.com/streamlink/streamlink/pull/6782))
- Build: added `typing-extensions` as a runtime dependency on Python 3.10, as it was already a transitive runtime dependency (via `exceptiongroup`) that was used as a fallback import since 8.1.0 ([#6813](https://github.com/streamlink/streamlink/pull/6813))

[Full changelog](https://github.com/streamlink/streamlink/compare/8.1.2...8.2.0)


## streamlink 8.1.2 (2026-01-18)

- Fixed: warnings when parsing HLS playlists with private-use language subtags ([#6780](https://github.com/streamlink/streamlink/pull/6780))
- Updated plugins:
  - youtube: fixed live streams ([#6777](https://github.com/streamlink/streamlink/pull/6777))

[Full changelog](https://github.com/streamlink/streamlink/compare/8.1.1...8.1.2)


## streamlink 8.1.1 (2026-01-17)

- Fixed: `--stream-segmented-queue-deadline` not being applied correctly to the Streamlink session options ([#6758](https://github.com/streamlink/streamlink/pull/6758))
- Changed: `--hls-segment-ignore-names` to not hardcode `.ts` HLS segment file name extensions ([#6747](https://github.com/streamlink/streamlink/pull/6747))
- Updated plugins:
  - dailymotion: fixed 403 HLS playlist responses ([#6773](https://github.com/streamlink/streamlink/pull/6773))
  - pluto: fixed url matchers and ad detection ([#6767](https://github.com/streamlink/streamlink/pull/6767))
  - soop: fixed CDN mapping for `ld_cdn` based regions ([#6749](https://github.com/streamlink/streamlink/pull/6749))
- Build: removed unneeded `wheel` dependency from `build-system.requires` and the `build` dependency group ([#6754](https://github.com/streamlink/streamlink/pull/6754))

[Full changelog](https://github.com/streamlink/streamlink/compare/8.1.0...8.1.1)


## streamlink 8.1.0 (2025-12-14)

- Deprecated: `--hls-segment-queue-threshold` in favor of `--stream-segmented-queue-deadline` ([#6734](https://github.com/streamlink/streamlink/pull/6734))
- Improved: debug logging of segmented streams ([#6730](https://github.com/streamlink/streamlink/pull/6730))
- Updated plugins:
  - twitch: fixed clips GQL API query ([#6744](https://github.com/streamlink/streamlink/pull/6744))
- Tests: removed accidental `pytest_cov` dependency when running tests ([#6727](https://github.com/streamlink/streamlink/pull/6727))

[Full changelog](https://github.com/streamlink/streamlink/compare/8.0.0...8.1.0)


## streamlink 8.0.0 (2025-11-11)

- BREAKING: dropped support for [EOL Python 3.9](https://peps.python.org/pep-0596/#lifespan) ([#6674](https://github.com/streamlink/streamlink/pull/6674))
- BREAKING/API: [removed deprecated `url_master` from `HLSStream`/`MuxedHLSStream`](https://streamlink.github.io/migrations.html#hlsstream-url-master-argument) ([#6688](https://github.com/streamlink/streamlink/pull/6688))
- BREAKING/dependencies: bumped version requirement of [`urllib3` to `>=2.0.0`](https://urllib3.readthedocs.io/en/stable/v2-migration-guide.html) ([#6686](https://github.com/streamlink/streamlink/pull/6686))
- Added: `--stream-segmented-duration` in favor of `--hls-duration` (now deprecated), which affects HLS, DASH and other segmented stream types ([#6705](https://github.com/streamlink/streamlink/pull/6705))
- Added: `duration` parameter to `dash://` streams (`DASHStream`) ([#6705](https://github.com/streamlink/streamlink/pull/6705))
- Added: `--ffmpeg-validation-timeout` for being able to increase the time for validating the FFmpeg executable (`--ffmpeg-ffmpeg`) ([#6716](https://github.com/streamlink/streamlink/pull/6716))
- Added: Flatpak player detection for VLC and mpv ([#6717](https://github.com/streamlink/streamlink/pull/6717), [#6723](https://github.com/streamlink/streamlink/pull/6723))
- Refactored: parts of the internal `SegmentedStream`, `HLSStream` and `DASHStream` implementations (WIP) ([#6696](https://github.com/streamlink/streamlink/pull/6696), [#6707](https://github.com/streamlink/streamlink/pull/6707), [#6709](https://github.com/streamlink/streamlink/pull/6709))
- Updated plugins:
  - aloula: fixed livestream schema ([#6662](https://github.com/streamlink/streamlink/pull/6662))
  - btv: rewritten and fixed plugin ([#6691](https://github.com/streamlink/streamlink/pull/6691))
  - chzzk: added support for in-progress VODs via live-rewind streams ([#6675](https://github.com/streamlink/streamlink/pull/6675))
  - dlive: fixed streams expiring after 5 minutes ([#6695](https://github.com/streamlink/streamlink/pull/6695))
  - goodgame: updated matches, switched API endpoints ([#6714](https://github.com/streamlink/streamlink/pull/6714))
  - nhkworld: removed plugin ([#6677](https://github.com/streamlink/streamlink/pull/6677))
  - rtve: fixed validation schema ([#6701](https://github.com/streamlink/streamlink/pull/6701))
  - twitch: fixed access token acquirement and various persisted GraphQL query IDs ([#6720](https://github.com/streamlink/streamlink/pull/6720), [#6721](https://github.com/streamlink/streamlink/pull/6721))
  - twitch: added `--twitch-supported-codecs` for access to higher quality streams ([#5769](https://github.com/streamlink/streamlink/pull/5769))
- Dependencies: dropped optional `zstandard` dependency on Python 3.14 and above ([#6683](https://github.com/streamlink/streamlink/pull/6683))
- Tests: bumped version requirement of `pytest` to `>=8.4.0` ([#6612](https://github.com/streamlink/streamlink/pull/6612))
- Docs: refactored docs config and custom Sphinx extensions, added `make` options for disabling various components for offline building ([#6668](https://github.com/streamlink/streamlink/pull/6668), [#6669](https://github.com/streamlink/streamlink/pull/6669))
- Docs: fixed compatibility with `docutils==0.22.2` ([#6699](https://github.com/streamlink/streamlink/pull/6699))

[Full changelog](https://github.com/streamlink/streamlink/compare/7.6.0...8.0.0)
