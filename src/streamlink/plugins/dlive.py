"""
Plugin for dlive.tv
"""
import re

from streamlink.plugin import Plugin
from streamlink.plugin.api import validate
from streamlink.stream import HLSStream
from streamlink.utils import parse_json
from streamlink import NoStreamsError


QUALITY_WEIGHTS = {
   "src": 1080,
}


class dlive(Plugin):
    _url_re = re.compile(r"https?://(?:www\.)?dlive\.tv/")

    _INFO_SCHEMA = validate.Schema({
                                    "data": {
                                        "userByDisplayName": {
                                            "username": validate.text
                                        }
                                    }
                                }
                            )

    @classmethod
    def can_handle_url(cls, url):
        return cls._url_re.match(url)

    @classmethod
    def stream_weight(cls, key):
        weight = QUALITY_WEIGHTS.get(key)
        if weight:
            return weight, "dlive"

        return Plugin.stream_weight(key)

    def _get_streams(self):
        reqUrl = "https://graphigo.prd.dlive.tv/"
        displayname = self.url[self.url.rfind('/') + 1:]
        jsonData = {
            "operationName": "LivestreamChatroomInfo",
            "variables":
            {
                "displayname": displayname,
                "isLoggedIn": False,
                "limit": 20
            },
            "query":
                """query LivestreamChatroomInfo($displayname: String!, \
                    $isLoggedIn: Boolean!, $limit: Int!)
                {
                    userByDisplayName(displayname: $displayname)
                    {
                        id
                        ...VLivestreamChatroomFrag
                        __typename
                    }
                }
                fragment VLivestreamChatroomFrag on User
                {
                    id
                    isFollowing @include(if: $isLoggedIn)
                    role @include(if: $isLoggedIn)
                    myRoomRole @include(if: $isLoggedIn)
                    isSubscribing @include(if: $isLoggedIn)
                    ...VStreamChatroomHeaderFrag
                    ...VStreamChatroomListFrag
                    ...StreamChatroomInputFrag
                    chats(count: 50)
                    {
                        type

                        ... on ChatGift
                        {
                            id
                            gift
                            amount
                            ...VStreamChatSenderInfoFrag
                            __typename
                        }

                        ... on ChatHost
                        {
                            id
                            viewer
                            ...VStreamChatSenderInfoFrag
                            __typename
                        }

                        ... on ChatSubscription
                        {
                            id
                            month
                            ...VStreamChatSenderInfoFrag
                            __typename
                        }

                        ... on ChatText
                        {
                            id
                            content
                            ...VStreamChatSenderInfoFrag
                            __typename
                        }

                        ... on ChatModerator
                        {
                            id
                            add
                            ...VStreamChatSenderInfoFrag
                            subscribing
                            role
                            roomRole
                            sender
                            {
                                id
                                username
                                displayname
                                avatar
                                partnerStatus
                                __typename
                            }
                            __typename
                        }

                        ... on ChatFollow
                        {
                            id
                            ...VStreamChatSenderInfoFrag
                            __typename
                        }

                        ... on ChatEmoteAdd
                        {
                            id
                            emote
                            ...VStreamChatSenderInfoFrag
                            subscribing
                            role
                            roomRole
                            sender
                            {
                                id
                                username
                                displayname
                                avatar
                                partnerStatus
                                __typename
                            }
                            __typename
                        }
                        __typename
                    }
                    __typename
                }

                fragment VStreamChatroomHeaderFrag on User
                {
                    id
                    username
                    displayname
                    livestream
                    {
                        id
                        permlink
                        __typename
                    }
                    ...VTopContributorsFrag
                    __typename
                }

                fragment VTopContributorsFrag on User
                {
                    id
                    displayname
                    livestream
                    {
                        id
                        __typename
                    }
                    __typename
                }

                fragment VStreamChatroomListFrag on User
                {
                    ...VStreamChatRowStreamerFrag
                    ...PinnedGiftsFrag
                    __typename
                }

                fragment VStreamChatRowStreamerFrag on User
                {
                    displayname
                    ...VStreamChatRowSenderInfoStreamerFrag
                    ...VStreamChatProfileCardStreamerFrag
                    ...StreamChatTextRowStreamerFrag
                    __typename
                }

                fragment VStreamChatRowSenderInfoStreamerFrag on User
                {
                    id
                    subSetting
                    {
                        badgeText
                        badgeColor
                        textColor
                        __typename
                    }
                    __typename
                }

                fragment VStreamChatProfileCardStreamerFrag on User
                {
                    id
                    username
                    myRoomRole @include(if: $isLoggedIn)
                    role
                    __typename
                }

                fragment StreamChatTextRowStreamerFrag on User
                {
                    id
                    username
                    myRoomRole @include(if: $isLoggedIn)
                    emote @include(if: $isLoggedIn)
                    {
                        channel
                        {
                            list
                            {
                                name
                                username
                                sourceURL
                                mimeType
                                level
                                type
                                __typename
                            }
                            __typename
                        }
                        __typename
                    }
                    __typename
                }

                fragment PinnedGiftsFrag on User
                {
                    id
                    recentDonations(limit: $limit)
                    {
                        user
                        {
                            ...VDliveAvatarFrag
                            ...VDliveNameFrag
                            __typename
                        }
                        ...PinnedGiftItemFrag
                        __typename
                    }
                    __typename
                }

                fragment VDliveAvatarFrag on User {  avatar  __typename}
                fragment VDliveNameFrag on User
                {
                    displayname
                    partnerStatus
                    __typename
                }

                fragment PinnedGiftItemFrag on DonationBlock
                {
                    user
                    {
                        id
                        username
                        displayname
                        ...VDliveAvatarFrag
                        ...VDliveNameFrag
                        __typename
                    }
                    count
                    type
                    updatedAt
                    expiresAt
                    expirationTime
                    __typename
                }

                fragment StreamChatroomInputFrag on User
                {
                    chatMode
                    chatInterval
                    myRoomRole @include(if: $isLoggedIn)
                    livestream
                    {
                        permlink
                        creator {      username      __typename    }
                        __typename
                    }
                    ...StreamChatMemberManageTabFrag
                    ...StreamChatModeSettingsFrag
                    ...EmoteBoardStreamerFrag
                    __typename
                }

                fragment StreamChatMemberManageTabFrag on User
                {
                    id
                    username
                    displayname
                    myRoomRole @include(if: $isLoggedIn)
                    __typename
                }

                fragment StreamChatModeSettingsFrag on User
                {
                    id
                    chatMode
                    allowEmote
                    chatInterval
                    __typename
                }

                fragment EmoteBoardStreamerFrag on User
                {
                    id
                    username
                    partnerStatus
                    myRoomRole @include(if: $isLoggedIn)
                    emote @include(if: $isLoggedIn)
                    {
                        channel
                        {
                            list
                            {
                                name
                                username
                                sourceURL
                                mimeType
                                level
                                type
                                __typename
                            }
                            __typename
                        }
                        __typename
                    }
                    __typename
                }

                fragment VStreamChatSenderInfoFrag on SenderInfo
                {
                    subscribing
                    role
                    roomRole
                    sender
                    {
                        id
                        username
                        displayname
                        avatar
                        partnerStatus
                        __typename
                    }
                __typename
                }
                """
        }
        res = self.session.http.post(reqUrl, json=jsonData)

        jsonres = self.session.http.json(res, schema=self._INFO_SCHEMA)

        hls_url = "https://live.prd.dlive.tv/hls/live/" \
            + jsonres["data"]["userByDisplayName"]["username"] + ".m3u8"

        try:
            return HLSStream.parse_variant_playlist(self.session, hls_url)
        except Exception:
            raise NoStreamsError(self.url)


__plugin__ = dlive
