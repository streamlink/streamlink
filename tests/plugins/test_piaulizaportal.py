from streamlink.plugins.piaulizaportal import PIAULIZAPortal
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlPIAULIZAPortal(PluginCanHandleUrl):
    __plugin__ = PIAULIZAPortal

    should_match_groups = [
        (
            "https://ulizaportal.jp/pages/005f18b7-e810-5618-cb82-0987c5755d44",
            {"id": "005f18b7-e810-5618-cb82-0987c5755d44"},
        ),
        (
            "https://ulizaportal.jp/pages/005e1b23-fe93-5780-19a0-98e917cc4b7d"
            + "?expires=4102412400&signature=f422a993b683e1068f946caf406d211c17d1ef17da8bef3df4a519502155aa91&version=1",
            {"id": "005e1b23-fe93-5780-19a0-98e917cc4b7d"},
        ),
    ]

    should_not_match = [
        "https://ulizaportal.jp/pages/",
        "https://ulizaportal.jp/pages/invalid-id",
    ]
