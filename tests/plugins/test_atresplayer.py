from unittest.mock import Mock

import pytest

from streamlink.plugins.atresplayer import AtresPlayer
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlAtresPlayer(PluginCanHandleUrl):
    __plugin__ = AtresPlayer

    should_match = [
        "https://www.atresplayer.com/directos/antena3/",
        "https://www.atresplayer.com/directos/lasexta/",
        "https://www.atresplayer.com/directos/antena3-internacional/",
    ]

    should_not_match = [
        "https://www.atresplayer.com/flooxer/programas/unas/temporada-1/dario-eme-hache-sindy-takanashi-entrevista_123/",
    ]


class TestAtresPlayer:
    @pytest.mark.parametrize(
        ("url", "expected"),
        [
            ("http://www.atresplayer.com/directos/antena3", "https://www.atresplayer.com/directos/antena3/"),
            ("http://www.atresplayer.com/directos/antena3/", "https://www.atresplayer.com/directos/antena3/"),
            ("https://www.atresplayer.com/directos/antena3", "https://www.atresplayer.com/directos/antena3/"),
            ("https://www.atresplayer.com/directos/antena3/", "https://www.atresplayer.com/directos/antena3/"),
        ],
    )
    def test_url(self, url, expected):
        plugin = AtresPlayer(Mock(), url)
        assert plugin.url == expected
