import pytest

from streamlink.options import Options
from streamlink.plugins.soop import Soop
from streamlink.session import Streamlink
from tests.plugins import PluginCanHandleUrl


class TestPluginCanHandleUrlSoop(PluginCanHandleUrl):
    __plugin__ = Soop

    should_match_groups = [
        ("https://play.sooplive.co.kr/CHANNEL", {"channel": "CHANNEL"}),
        ("https://play.sooplive.co.kr/CHANNEL/0123456789", {"channel": "CHANNEL", "bno": "0123456789"}),
        ("https://play.afreecatv.com/CHANNEL", {"channel": "CHANNEL"}),
        ("https://play.afreecatv.com/CHANNEL/0123456789", {"channel": "CHANNEL", "bno": "0123456789"}),
    ]

    should_not_match = [
        "https://sooplive.co.kr/CHANNEL",
        "https://sooplive.co.kr/CHANNEL/0123456789",
        "https://afreecatv.com/CHANNEL",
        "https://afreecatv.com/CHANNEL/0123456789",
    ]


@pytest.mark.parametrize(
    ("plugin_options", "expected"),
    [
        pytest.param(
            {"username": "username", "password": "password", "purge-credentials": True, "stream-password": "foo"},
            {"username": "username", "password": "password", "purge-credentials": True, "stream-password": "foo"},
            id="regular-options",
        ),
        pytest.param(
            {
                "afreeca-username": "username",
                "afreeca-password": "password",
                "afreeca-purge-credentials": True,
                "afreeca-stream-password": "foo",
            },
            {
                "username": "username",
                "password": "password",
                "purge-credentials": True,
                "stream-password": "foo",
                "afreeca-username": "username",
                "afreeca-password": "password",
                "afreeca-purge-credentials": True,
                "afreeca-stream-password": "foo",
            },
            id="deprecated-options",
        ),
        pytest.param(
            {
                "username": "username1",
                "password": "password1",
                "purge-credentials": True,
                "stream-password": "foo",
                "afreeca-username": "username2",
                "afreeca-password": "password2",
                "afreeca-purge-credentials": False,
                "afreeca-stream-password": "bar",
            },
            {
                "username": "username1",
                "password": "password1",
                "purge-credentials": True,
                "stream-password": "foo",
                "afreeca-username": "username2",
                "afreeca-password": "password2",
                "afreeca-purge-credentials": False,
                "afreeca-stream-password": "bar",
            },
            id="regular-and-deprecated-options",
        ),
    ],
)
def test_options(session: Streamlink, plugin_options: dict, expected: dict):
    options = Options()
    options.update(plugin_options)
    plugin = Soop(session, "https://play.soop.co.kr/CHANNEL/0123456789", options)
    assert dict(plugin.options.items()) == expected
