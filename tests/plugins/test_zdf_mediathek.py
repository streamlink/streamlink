from streamlink.plugins.zdf_mediathek import ZDFMediathek
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlZDFMediathek(PluginCanHandleUrl):
    __plugin__ = ZDFMediathek

    should_match_groups = [
        (
            "https://www.zdf.de/play/live-tv/sender/zdf-live-beitrag-100",
            {"category": "live-tv", "video_id": "zdf-live-beitrag-100"},
        ),
        (
            "https://www.zdf.de/play/live-tv/sender/zdfinfo-live-beitrag-100",
            {"category": "live-tv", "video_id": "zdfinfo-live-beitrag-100"},
        ),
        (
            "https://www.zdf.de/play/live-tv/sender/arte-livestream-100",
            {"category": "live-tv", "video_id": "arte-livestream-100"},
        ),
        (
            "https://www.zdf.de/play/magazine/heute-106/260906-heute-sendung-17-uhr-100",
            {"category": "magazine", "video_id": "260906-heute-sendung-17-uhr-100"},
        ),
        (
            "https://www.zdf.de/play/dokus/terra-x-unsere-waelder-100/unsere-waelder-ein-jahr-unter-baeumen-100",
            {"category": "dokus", "video_id": "unsere-waelder-ein-jahr-unter-baeumen-100"},
        ),
    ]
