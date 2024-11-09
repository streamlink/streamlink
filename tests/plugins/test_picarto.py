from streamlink.plugins.picarto import Picarto
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlPicarto(PluginCanHandleUrl):
    __plugin__ = Picarto

    should_match_groups = [
        (("user", "https://picarto.tv/example"), {"user": "example"}),
        (("user", "https://www.picarto.tv/example"), {"user": "example"}),
        (("vod", "https://www.picarto.tv/example/videos/123456"), {"vod_id": "123456"}),
        (("streampopout", "https://www.picarto.tv/streampopout/example/public"), {"po_user": "example"}),
        (("videopopout", "https://www.picarto.tv/videopopout/123456"), {"po_vod_id": "123456"}),
    ]

    should_not_match = [
        "https://picarto.tv/",
        "https://www.picarto.tv/example/",
        "https://www.picarto.tv/example/videos/abc123",
        "https://www.picarto.tv/streampopout/example/notpublic",
        "https://www.picarto.tv/videopopout/abc123",
    ]
