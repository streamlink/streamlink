from streamlink.plugins.mangomolo import Mangomolo
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlMangomolo(PluginCanHandleUrl):
    __plugin__ = Mangomolo

    should_match = [
        (
            "mangomoloplayer",
            "https://player.mangomolo.com/v1/live?id=MTk1&channelid=MzU1&countries=bnVsbA==&w=100%25&h=100%25"
            + "&autoplay=true&filter=none&signature=9ea6c8ed03b8de6e339d6df2b0685f25&app_id=43",
        ),
        (
            "51comkw",
            "https://51.com.kw/live",
        ),
        (
            "51comkw",
            "https://51.com.kw/live/",
        ),
        (
            "51comkw",
            "https://51.com.kw/live/355/AlKuwait",
        ),
        (
            "51comkw",
            "https://51.com.kw/live/361/KTV2",
        ),
        (
            "51comkw",
            "https://51.com.kw/live/356/News",
        ),
        (
            "51comkw",
            "https://51.com.kw/live/362/Sport",
        ),
        (
            "51comkw",
            "https://51.com.kw/live/357/Sport2",
        ),
    ]
