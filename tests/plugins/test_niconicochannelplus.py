from streamlink.plugins.niconicochannelplus import NicoNicoChannelPlus
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlNicoNicoChannelPlus(PluginCanHandleUrl):
    __plugin__ = NicoNicoChannelPlus

    should_match = [
        # video urls
        #   normal channel name.
        'https://nicochannel.jp/olchannel/video/smq9UriUQ9PU65jTjVxh2PVo',
        #   numbers in channel name.
        'https://nicochannel.jp/dateno8noba/video/smVGqtKpdmva4Mcrw7rbeQ8Y',
        #   hyphens in channel name.
        'https://nicochannel.jp/mimimoto-ayaka/video/smRS96YpmDJr24YpWFZziG4L',
        #   underscores in channel name.
        'https://nicochannel.jp/sakaguchi_kugimiya/video/smnSFttxbkjZDBwZMMj8CgsJ',

        # live urls
        #   normal channel name.
        'https://nicochannel.jp/example/live/sm3Xample',
    ]

    should_match_groups = [
        # video urls
        (
            'https://nicochannel.jp/olchannel/video/smq9UriUQ9PU65jTjVxh2PVo',
            {
                'id': 'smq9UriUQ9PU65jTjVxh2PVo',
                'channel': 'olchannel',
            }
        ),
        (
            'https://nicochannel.jp/dateno8noba/video/smVGqtKpdmva4Mcrw7rbeQ8Y',
            {
                'id': 'smVGqtKpdmva4Mcrw7rbeQ8Y',
                'channel': 'dateno8noba',
            }
        ),
        (
            'https://nicochannel.jp/mimimoto-ayaka/video/smRS96YpmDJr24YpWFZziG4L',
            {
                'id': 'smRS96YpmDJr24YpWFZziG4L',
                'channel': 'mimimoto-ayaka',
            }
        ),
        (
            'https://nicochannel.jp/sakaguchi_kugimiya/video/smnSFttxbkjZDBwZMMj8CgsJ',
            {
                'id': 'smnSFttxbkjZDBwZMMj8CgsJ',
                'channel': 'sakaguchi_kugimiya',
            }
        ),
        # live urls
        (
            'https://nicochannel.jp/example/live/sm3Xample',
            {
                'id': 'sm3Xample',
                'channel': 'example',
            }
        ),
    ]

    should_not_match = [
        # Niconico Channel Plus
        #   portal
        'https://portal.nicochannel.jp/',
        #   channel home pages
        'https://nicochannel.jp/example',
        #   channel live list
        'https://nicochannel.jp/example/lives',
        #   channel video list
        'https://nicochannel.jp/example/videos',
        #   invalid urls
        'https://nicochannel.jp/'
        'https://nicochannel.jp/example/live',
        'https://nicochannel.jp/example/video',

        # Niconico Channel
        #   portal
        'https://ch.nicovideo.jp/',
        #   channel home pages
        'https://ch.nicovideo.jp/ch0000000',
        'https://ch.nicovideo.jp/example',
    ]
