"""
$description Social media platform X, formerly known as Twitter, owned by X Corp.
$url x.com
$url twitter.com
$type live, vod
$metadata id
$metadata author
$metadata title
"""

import logging
import re
from json import dumps as json_dumps

from streamlink.plugin import Plugin, pluginmatcher
from streamlink.plugin.api import validate
from streamlink.stream.hls import HLSStream
from streamlink.stream.http import HTTPStream


log = logging.getLogger(__name__)


@pluginmatcher(
    name="live",
    pattern=re.compile(r"https?://(?:www\.)?(?:x|twitter)\.com/i/broadcasts/(?P<id>[^/?]+)"),
)
@pluginmatcher(
    name="vod",
    pattern=re.compile(r"https?://(?:www\.)?(?:x|twitter)\.com/(?P<user>\w+)/status/(?P<id>\d+)(?:/video/(?P<idx>\d+))?"),
)
class X(Plugin):
    # https://abs.twimg.com/responsive-web/client-web/main.73234c5a.js
    _API_TOKEN = "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"

    _API_URL_BROADCAST_QUERY = "https://api.x.com/graphql/YaG1VzpA3PhhtalTJCZGFA/BroadcastQuery"
    _API_URL_LIVE_VIDEO_STREAM = "https://api.x.com/1.1/live_video_stream/status/{media_key}.json"
    _API_URL_TWEET_RESULT_BY_REST_ID = "https://api.x.com/graphql/taYqW6MhmUrkLfkp6vlXgw/TweetResultByRestId"

    # some features appear to be required, so just copy the whole request data
    _API_FEATURES = {
        "creator_subscriptions_tweet_preview_api_enabled": True,
        "premium_content_api_read_enabled": False,
        "communities_web_enable_tweet_community_results_fetch": True,
        "c9s_tweet_anatomy_moderator_badge_enabled": True,
        "responsive_web_grok_analyze_button_fetch_trends_enabled": False,
        "responsive_web_grok_analyze_post_followups_enabled": False,
        "responsive_web_grok_share_attachment_enabled": True,
        "articles_preview_enabled": True,
        "profile_label_improvements_pcf_label_in_post_enabled": False,
        "rweb_tipjar_consumption_enabled": True,
        "responsive_web_graphql_exclude_directive_enabled": True,
        "verified_phone_label_enabled": False,
        "responsive_web_edit_tweet_api_enabled": True,
        "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
        "view_counts_everywhere_api_enabled": True,
        "longform_notetweets_consumption_enabled": True,
        "responsive_web_twitter_article_tweet_consumption_enabled": True,
        "tweet_awards_web_tipping_enabled": False,
        "creator_subscriptions_quote_tweet_preview_enabled": False,
        "freedom_of_speech_not_reach_fetch_enabled": True,
        "standardized_nudges_misinfo": True,
        "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
        "rweb_video_timestamps_enabled": True,
        "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
        "longform_notetweets_rich_text_read_enabled": True,
        "longform_notetweets_inline_media_enabled": True,
        "responsive_web_graphql_timeline_navigation_enabled": True,
        "responsive_web_enhance_cards_enabled": False,
    }

    _STATE_RUNNING = "Running"
    _STATE_ENDED = "Ended"

    def _get_guest_token(self):
        return self.session.http.get(
            self.url,
            # required for the document.cookie script tag to be included
            params={"mx": 2},
            schema=validate.Schema(
                validate.parse_html(),
                validate.xml_xpath_string(".//script[contains(text(),'document.cookie')][contains(text(),'gt=')][1]/text()"),
                validate.none_or_all(
                    re.compile(r"""document\.cookie\s*=\s*["']gt=(?P<cookie>\w+)"""),
                    validate.get("cookie"),
                ),
            ),
        )

    def _query_api(self, url, variables=None, **kwargs):
        params = kwargs.pop("params", {})
        params["variables"] = json_dumps(variables or {}, separators=(",", ":"))
        params["features"] = json_dumps(self._API_FEATURES, separators=(",", ":"))

        headers = kwargs.pop("headers", {})
        headers["Content-Type"] = "application/json"
        headers["Authorization"] = f"Bearer {self._API_TOKEN}"

        return self.session.http.get(
            url,
            params=params,
            headers=headers,
            **kwargs,
        )

    def _query_api_broadcast(self, broadcast_id):
        return self._query_api(
            self._API_URL_BROADCAST_QUERY,
            variables={
                "id": broadcast_id,
            },
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "data": {
                        "broadcast": {
                            "media_key": str,
                            "status": str,
                            "state": str,
                            "periscope_user": {
                                "username": str,
                            },
                        },
                    },
                },
                validate.get(("data", "broadcast")),
                validate.union_get(
                    "state",
                    "media_key",
                    ("periscope_user", "username"),
                    "status",
                ),
            ),
        )

    def _query_api_tweet(self, tweet_id, guest_token):
        schema_tweet_unavailable = validate.all(
            {
                "__typename": "TweetUnavailable",
            },
            validate.transform(lambda _: None),
        )
        schema_tweet = validate.all(
            {
                "__typename": "Tweet",
                "legacy": {
                    "entities": {
                        validate.optional("media"): [
                            validate.all(
                                {
                                    "type": str,
                                    validate.optional("video_info"): validate.all(
                                        {
                                            "variants": [
                                                validate.all(
                                                    {
                                                        "content_type": str,
                                                        validate.optional("bitrate"): int,
                                                        "url": validate.url(),
                                                    },
                                                    validate.union_get(
                                                        "content_type",
                                                        "bitrate",
                                                        "url",
                                                    ),
                                                ),
                                            ],
                                        },
                                        validate.get("variants"),
                                    ),
                                },
                                validate.union_get("type", "video_info"),
                            ),
                        ],
                    },
                },
            },
            validate.get(("legacy", "entities", "media")),
        )

        return self._query_api(
            self._API_URL_TWEET_RESULT_BY_REST_ID,
            variables={
                "tweetId": tweet_id,
                "withCommunity": False,
                "includePromotedContent": False,
                "withVoice": False,
            },
            headers={
                "X-Guest-Token": guest_token,
            },
            cookies={
                "gt": guest_token,
            },
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "data": {
                        "tweetResult": {
                            validate.optional("result"): validate.any(
                                schema_tweet_unavailable,
                                schema_tweet,
                            ),
                        },
                    },
                },
                validate.get(("data", "tweetResult", "result")),
            ),
        )

    def _get_streams_live(self):
        self.id = self.match["id"]

        state, media_key, self.author, self.title = self._query_api_broadcast(self.id)
        if not media_key:
            return

        log.debug(f"{media_key=}")

        if state not in (self._STATE_RUNNING, self._STATE_ENDED):
            log.error("The stream is inaccessible")
            return

        hls_url = self.session.http.get(
            self._API_URL_LIVE_VIDEO_STREAM.format(media_key=media_key),
            headers={
                "Authorization": f"Bearer {self._API_TOKEN}",
            },
            schema=validate.Schema(
                validate.parse_json(),
                {
                    "source": {
                        "location": validate.url(path=validate.endswith(".m3u8")),
                    },
                },
                validate.get(("source", "location")),
            ),
        )

        return HLSStream.parse_variant_playlist(self.session, hls_url)

    def _get_streams_vod(self):
        self.id = self.match["id"]
        self.author = self.match["user"]
        idx = int(self.match["idx"] or "1") - 1

        guest_token = self._get_guest_token()
        log.debug(f"{guest_token=}")

        if not (items := self._query_api_tweet(self.id, guest_token)):
            return

        if (length := len(items)) == 1:
            idx = 0
        elif length < 1 or idx >= length:
            return

        item_type, variants = items[idx]
        if item_type != "video":
            return

        streams = {}
        for content_type, bitrate, url in variants:
            if content_type == "application/x-mpegURL":
                streams.update(HLSStream.parse_variant_playlist(self.session, url))
            elif content_type == "video/mp4" and bitrate:
                streams[f"{bitrate // 1024}k"] = HTTPStream(self.session, url)

        return streams

    def _get_streams(self):
        if self.matches["live"]:
            return self._get_streams_live()
        if self.matches["vod"]:
            return self._get_streams_vod()


__plugin__ = X
