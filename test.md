## Youtube plugin

The plugin was converted from a single `youtube.py` file into a Python package (`src/streamlink/plugins/youtube/`). The new architecture introduces an extractor chain and a Deno JavaScript solver for YouTube's n-parameter challenge.


---

### Package Structure

```
youtube/
├── __init__.py          # Exports __plugin__ = Youtube
├── plugin.py            # Entry point, URL matching, extractor orchestration
├── extractors.py        # Extractors for different entities
├── deno.py              # Deno subprocess solver for n-challenges
├── structures.py        # Shared dataclasses, protocols, enums, Context singleton
├── youtube.py           # Original plugin kept as fallback
└── solver/
    ├── __init__.py      # Reads bundled JS files as strings
    ├── lib.min.js       # Bundled JS library for the solver (from yt-dlp-ejs)
    └── core.min.js      # Bundled JS core solver logic (from yt-dlp-ejs)
```

---

### n-Parameter Challenge Solver

YouTube embeds a token (`n` parameter) in HLS manifest URL paths (`/n/<token>/`). If not solved, YouTube returns 403 for the video segments. The solver works as follows:

1. `VideoExtractor._extract_hls()` detects `/n/<token>/` in each manifest URL path
2. It calls `DenoJCP.solve()` which fetches the YouTube player JS and builds deno stdin that inlines `lib.min.js` and `core.min.js` (from [yt-dlp-ejs](https://github.com/yt-dlp/ejs/tree/main))
3. Starts a `deno run` subprocess with the prebuilt stdin
4. Deno runs with all network access, npm, remote imports, module cache, and config disabled (`--no-remote`, `--no-npm`, `--cached-only`, `--no-config`, etc.) — only the bundled scripts and player source are executed
5. Parses the JSON output into an `NChallengeOutput` mapping original token -> solved token
6. Returns `NChallengeOutput` back to `VideoExtractor` which replaces the original token in the manifest URL

If [Deno](https://deno.com/) is not installed, the error message explicitly directs the user to the Deno installation page.

---


### Stream Probing and Fallback (`plugin.py`)

After HLS manifest URLs are collected, `_check_streams()` parses each as a variant playlist via `HLSStream.parse_variant_playlist()` and probes reachability by opening the first variant and reading 64 bytes with a 2-second timeout. If the n-challenge is solved incorrectly, YouTube will return 403 for every video segment. Unreachable streams are discarded with a warning.

If the entire extractor chain fails, the plugin transparently falls back to the original `youtube.py` implementation (`YtOriginal`), stripping the `/streams` suffix from the URL if present.

---

### Extractors (`extractors.py`)
Contains three extractors: `StreamsExtractor`, `LiveExtractor`, `VideoExtractor`. Each extractor implements an `_extract(url)` method that returns either a redirect to the next extractor or a list of HLS URLs.

#### 1. `StreamsExtractor`
- Matches: `.../streams` URLs
- Parses the active (non-upcoming) streams from `ytInitialData` -> `richGridRenderer`
- Selects a stream based on the `--youtube-stream` plugin-specific option
- Returns a `NextExtractor` with the resolved watch URL

#### 2. `LiveExtractor`
- Matches: `.../live` URLs
- Fetches the video ID from `ytInitialData` -> `currentVideoEndpoint.watchEndpoint.videoId`
- Returns a `NextExtractor` with the resolved watch URL

#### 3. `VideoExtractor`
- Matches: `.../watch?v=ID`
- Fetches player responses using two clients: `web_safari` and `android_vr` 
- Collects `hlsManifestUrl` values from `streamingData` in each player response
- Solves the n-parameter challenge in each manifest URL via `DenoJCP`
- Returns an `ExtractorResult` with the final list of solved HLS manifest URLs

---

### Plugin-specific option `--youtube-stream`

| Value         | Behavior                                                        |
|---------------|-----------------------------------------------------------------|
| `popular`     | Picks the stream with the highest viewer count                  |
| `first`       | Picks the first stream in the listing                           |
| `last`        | Picks the last stream in the listing                            |
| `N` (integer) | Picks the Nth stream (1-based, clamped to last if out of range) |

Invalid values fall back to `popular` with a warning.

---

### Supported URL Formats

Handles the same formats as the original plugin can and in addition can handle `/streams` tab with help of plugin-specific option `--youtube-stream`
