import re

import pytest
import requests_mock as rm

import streamlink_cli.main
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.session import Streamlink


@pytest.fixture(autouse=True)
def _plugins(session: Streamlink):
    @pluginmatcher(re.compile(r"http://exists$"))
    class FakePlugin(Plugin):
        def _get_streams(self):  # pragma: no cover
            pass

    session.plugins.update({"plugin": FakePlugin})


@pytest.mark.parametrize(
    ("argv", "exit_code"),
    [
        pytest.param(
            ["--can-handle-url", "http://aborted"],
            130,
            id="aborted",
        ),
        pytest.param(
            ["--can-handle-url", "http://exists"],
            0,
            id="exists",
        ),
        pytest.param(
            ["--can-handle-url", "http://exists-redirect"],
            0,
            id="exists-redirect",
        ),
        pytest.param(
            ["--can-handle-url", "http://missing"],
            1,
            id="missing",
        ),
        pytest.param(
            ["--can-handle-url", "http://missing-redirect"],
            1,
            id="missing-redirect",
        ),
        pytest.param(
            ["--can-handle-url-no-redirect", "http://exists"],
            0,
            id="noredirect-exists",
        ),
        pytest.param(
            ["--can-handle-url-no-redirect", "http://exists-redirect"],
            1,
            id="noredirect-exists-redirect",
        ),
        pytest.param(
            ["--can-handle-url-no-redirect", "http://missing"],
            1,
            id="noredirect-missing",
        ),
        pytest.param(
            ["--can-handle-url-no-redirect", "http://missing-redirect"],
            1,
            id="noredirect-missing-redirect",
        ),
    ],
    indirect=["argv"],
)
def test_can_handle_url(requests_mock: rm.Mocker, session: Streamlink, argv: list, exit_code: int):
    requests_mock.request(rm.ANY, "http://aborted", exc=KeyboardInterrupt)  # type: ignore[arg-type]
    requests_mock.request(rm.ANY, "http://exists", content=b"")
    requests_mock.request(rm.ANY, "http://exists-redirect", status_code=301, headers={"Location": "http://exists"})
    requests_mock.request(rm.ANY, "http://missing-redirect", status_code=301, headers={"Location": "http://missing"})

    with pytest.raises(SystemExit) as exc_info:
        streamlink_cli.main.main()
    assert exc_info.value.code == exit_code
