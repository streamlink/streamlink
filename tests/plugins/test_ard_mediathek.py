from streamlink.plugins.ard_mediathek import ARDMediathek
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlARDMediathek(PluginCanHandleUrl):
    __plugin__ = ARDMediathek

    should_match_groups = [
        (
            (
                "live",
                "https://www.ardmediathek.de/live/Y3JpZDovL2Rhc2Vyc3RlLmRlL2xpdmUvY2xpcC9hYmNhMDdhMy0zNDc2LTQ4NTEtYjE2Mi1mZGU4ZjY0NmQ0YzQ",
            ),
            {"id_live": "Y3JpZDovL2Rhc2Vyc3RlLmRlL2xpdmUvY2xpcC9hYmNhMDdhMy0zNDc2LTQ4NTEtYjE2Mi1mZGU4ZjY0NmQ0YzQ"},
        ),
        (
            (
                "live",
                "https://www.ardmediathek.de/live/Y3JpZDovL2Rhc2Vyc3RlLmRlL2xpdmUvY2xpcC9hYmNhMDdhMy0zNDc2LTQ4NTEtYjE2Mi1mZGU4ZjY0NmQ0YzQ?toolbarType=default",
            ),
            {"id_live": "Y3JpZDovL2Rhc2Vyc3RlLmRlL2xpdmUvY2xpcC9hYmNhMDdhMy0zNDc2LTQ4NTEtYjE2Mi1mZGU4ZjY0NmQ0YzQ"},
        ),
        (
            (
                "live",
                "https://www.ardmediathek.de/live/tagesschau24/Y3JpZDovL2Rhc2Vyc3RlLmRlL3RhZ2Vzc2NoYXUvbGl2ZXN0cmVhbQ",
            ),
            {"id_live": "Y3JpZDovL2Rhc2Vyc3RlLmRlL3RhZ2Vzc2NoYXUvbGl2ZXN0cmVhbQ"},
        ),
        (
            (
                "video",
                "https://www.ardmediathek.de/video/Y3JpZDovL3dkci5kZS9CZWl0cmFnLXNvcGhvcmEtZTJkYWIwMTEtZWRjOC00YTkwLThhOGQtOGMxNTJjMTFmOTVj",
            ),
            {"id_video": "Y3JpZDovL3dkci5kZS9CZWl0cmFnLXNvcGhvcmEtZTJkYWIwMTEtZWRjOC00YTkwLThhOGQtOGMxNTJjMTFmOTVj"},
        ),
        (
            (
                "video",
                "https://www.ardmediathek.de/video/maerchen-in-der-ard/hans-im-glueck/ndr/Y3JpZDovL25kci5kZS80NDI2XzIwMjItMTItMjUtMDktMjA?isChildContent",
            ),
            {"id_video": "Y3JpZDovL25kci5kZS80NDI2XzIwMjItMTItMjUtMDktMjA"},
        ),
        (
            (
                "video",
                "https://www.ardmediathek.de/video/heimatflimmern/wild-im-westen-die-eifel/wdr/Y3JpZDovL3dkci5kZS9CZWl0cmFnLXNvcGhvcmEtM2VlOGUzYWUtNTliNy00M2RiLWIyZTMtNTY3OWFkMjQyYWU1",
            ),
            {"id_video": "Y3JpZDovL3dkci5kZS9CZWl0cmFnLXNvcGhvcmEtM2VlOGUzYWUtNTliNy00M2RiLWIyZTMtNTY3OWFkMjQyYWU1"},
        ),
    ]
