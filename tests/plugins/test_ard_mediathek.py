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
                "https://www.ardmediathek.de/video/Y3JpZDovL2Rhc2Vyc3RlLmRlL3RhZ2Vzc2NoYXUvOWE4NGIzODgtZDEzNS00ZWU0LWI4ODEtZDYyNTQzYjg3ZmJlLzE",
            ),
            {"id_video": "Y3JpZDovL2Rhc2Vyc3RlLmRlL3RhZ2Vzc2NoYXUvOWE4NGIzODgtZDEzNS00ZWU0LWI4ODEtZDYyNTQzYjg3ZmJlLzE"},
        ),
        (
            (
                "video",
                "https://www.ardmediathek.de/video/arte/blackfish-der-killerwal/arte/Y3JpZDovL2FydGUudHYvdmlkZW9zLzA1MDMyNy0wMDAtQQ",
            ),
            {"id_video": "Y3JpZDovL2FydGUudHYvdmlkZW9zLzA1MDMyNy0wMDAtQQ"},
        ),
        (
            (
                "video",
                "https://www.ardmediathek.de/video/expeditionen-ins-tierreich/die-revolte-der-schimpansen/ndr/Y3JpZDovL25kci5kZS9jY2E3M2MzZS00ZTljLTRhOWItODE3MC05MjhjM2MwNWEyMDM?toolbarType=default",
            ),
            {"id_video": "Y3JpZDovL25kci5kZS9jY2E3M2MzZS00ZTljLTRhOWItODE3MC05MjhjM2MwNWEyMDM"},
        ),
    ]
