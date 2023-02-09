from streamlink.plugins.n13tv import N13TV
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlN13TV(PluginCanHandleUrl):
    __plugin__ = N13TV

    should_match = [
        "http://13tv.co.il/live",
        "https://13tv.co.il/live",
        "http://www.13tv.co.il/live/",
        "https://www.13tv.co.il/live/",
        "http://13tv.co.il/item/entertainment/ambush/season-02/episodes/ffuk3-2026112/",
        "https://13tv.co.il/item/entertainment/ambush/season-02/episodes/ffuk3-2026112/",
        "http://www.13tv.co.il/item/entertainment/ambush/season-02/episodes/ffuk3-2026112/",
        "https://www.13tv.co.il/item/entertainment/ambush/season-02/episodes/ffuk3-2026112/",
        "http://13tv.co.il/item/entertainment/tzhok-mehamatzav/season-01/episodes/vkdoc-2023442/",
        "https://13tv.co.il/item/entertainment/tzhok-mehamatzav/season-01/episodes/vkdoc-2023442/",
        "http://www.13tv.co.il/item/entertainment/tzhok-mehamatzav/season-01/episodes/vkdoc-2023442/",
        "https://www.13tv.co.il/item/entertainment/tzhok-mehamatzav/season-01/episodes/vkdoc-2023442/",
    ]
