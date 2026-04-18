from __future__ import annotations

from typing import TYPE_CHECKING

from streamlink.plugin.api import validate
from tests.plugins_remote import PluginTest


if TYPE_CHECKING:
    from streamlink.session import Streamlink


class TestPluginTwitch(PluginTest):
    @staticmethod
    def _gql_query(session: Streamlink, query: object, schema: validate.Schema):
        return session.http.post(
            "https://gql.twitch.tv/gql",
            headers={
                "Client-Id": "kimne78kx3ncx6brgo4mv6wki5h1ko",
            },
            json=query,
            schema=validate.Schema(
                validate.parse_json(),
                schema,
            ),
        )

    def remote_live(self, session: Streamlink) -> str | tuple[str, dict]:
        channel = self._gql_query(
            session,
            {
                "operationName": "BrowsePage_Popular",
                "variables": {
                    "imageWidth": 50,
                    "limit": 1,
                    "platformType": "all",
                    "options": {},
                    "sortTypeIsRecency": False,
                    "includeCostreaming": False,
                },
                "extensions": {
                    "persistedQuery": {
                        "version": 1,
                        "sha256Hash": "fb60a7f9b2fe8f9c9a080f41585bd4564bea9d3030f4d7cb8ab7f9e99b1cee67",
                    },
                },
            },
            schema=validate.Schema(
                {
                    "data": {
                        "streams": {
                            "edges": [
                                {
                                    "node": {
                                        "broadcaster": {
                                            "login": str,
                                        },
                                    },
                                },
                            ],
                        },
                    },
                },
                validate.get(("data", "streams", "edges", 0, "node", "broadcaster", "login")),
            ),
        )

        return f"https://www.twitch.tv/{channel}", {"force-client-integrity": True, "low-latency": True}

    def remote_vod(self, session: Streamlink) -> str | tuple[str, dict]:
        vod = self._gql_query(
            session,
            {
                "operationName": "FilterableVideoTower_Videos",
                "variables": {
                    "includePreviewBlur": False,
                    "limit": 1,
                    "channelOwnerLogin": "twitch",
                    "broadcastType": "ARCHIVE",
                    "videoSort": "TIME",
                },
                "extensions": {
                    "persistedQuery": {
                        "version": 1,
                        "sha256Hash": "67004f7881e65c297936f32c75246470629557a393788fb5a69d6d9a25a8fd5f",
                    },
                },
            },
            schema=validate.Schema(
                {
                    "data": {
                        "user": {
                            "videos": {
                                "edges": [
                                    {
                                        "node": {
                                            "id": str,
                                        },
                                    },
                                ],
                            },
                        },
                    },
                },
                validate.get(("data", "user", "videos", "edges", 0, "node", "id")),
            ),
        )

        return f"https://www.twitch.tv/videos/{vod}"

    def remote_clip(self, session: Streamlink) -> str | tuple[str, dict]:
        channel = "twitch"
        clip = self._gql_query(
            session,
            {
                "operationName": "ClipsCards__User",
                "variables": {
                    "login": channel,
                    "limit": 1,
                    "criteria": {
                        "filter": "ALL_TIME",
                        "shouldFilterByDiscoverySetting": False,
                    },
                    "cursor": None,
                },
                "extensions": {
                    "persistedQuery": {
                        "version": 1,
                        "sha256Hash": "1cd671bfa12cec480499c087319f26d21925e9695d1f80225aae6a4354f23088",
                    },
                },
            },
            schema=validate.Schema(
                {
                    "data": {
                        "user": {
                            "clips": {
                                "edges": [
                                    {
                                        "node": {
                                            "slug": str,
                                        },
                                    },
                                ],
                            },
                        },
                    },
                },
                validate.get(("data", "user", "clips", "edges", 0, "node", "slug")),
            ),
        )

        return f"https://www.twitch.tv/{channel}/clip/{clip}"
