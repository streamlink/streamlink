from streamlink.plugins.facebook import Facebook
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlFacebook(PluginCanHandleUrl):
    __plugin__ = Facebook

    should_match_groups = [
        (("share", "https://www.facebook.com/share/r/1CRiEHbJMR/"), {"share_id": "1CRiEHbJMR"}),
        (
            ("default", "https://www.facebook.com/mariana.conde1/videos/2254962351960559/"),
            {"user": "mariana.conde1", "video_id": "2254962351960559"},
        ),
        (
            ("default", "https://www.facebook.com/reel/1720478309005050"),
            {"video_id": "1720478309005050"},
        ),
        (
            ("default", "https://www.facebook.com/1324597932/videos/2254962351960559/?__so__=video_home_video_not_found"),
            {"user": "1324597932", "video_id": "2254962351960559"},
        ),
        (
            ("search", "https://www.facebook.com/watch/live/?ref=watch_permalink&v=1440067724656110"),
            {"video_id": "1440067724656110"},
        ),
    ]

    should_not_match = [
        "https://www.facebook.com",
    ]
