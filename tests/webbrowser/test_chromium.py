from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path, PurePosixPath, PureWindowsPath
from signal import SIGTERM
from typing import Any

import pytest
import requests_mock as rm
import trio
from requests import Timeout

from streamlink.compat import is_win32
from streamlink.exceptions import PluginError
from streamlink.session import Streamlink
from streamlink.webbrowser.chromium import ChromiumWebbrowser
from streamlink.webbrowser.exceptions import WebbrowserError


class TestInit:
    @pytest.mark.parametrize(
        ("executable", "resolve_executable", "raises"),
        [
            pytest.param(
                None,
                None,
                pytest.raises(
                    WebbrowserError,
                    match=r"^Could not find Chromium-based web browser executable: Please set the path ",
                ),
                id="Failure with unset path",
            ),
            pytest.param(
                "custom",
                None,
                pytest.raises(
                    WebbrowserError,
                    match=r"^Invalid web browser executable: custom$",
                ),
                id="Failure with custom path",
            ),
            pytest.param(
                None,
                "default",
                nullcontext(),
                id="Success with default path",
            ),
            pytest.param(
                "custom",
                "custom",
                nullcontext(),
                id="Success with custom path",
            ),
        ],
        indirect=["resolve_executable"],
    )
    def test_resolve_executable(self, resolve_executable, executable: str | None, raises: nullcontext):
        with raises:
            ChromiumWebbrowser(executable=executable)


class TestFallbacks:
    def test_win32(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("streamlink.webbrowser.chromium.is_win32", True)
        monkeypatch.setattr("streamlink.webbrowser.chromium.is_darwin", False)
        monkeypatch.setattr("streamlink.webbrowser.chromium.Path", PureWindowsPath)
        monkeypatch.setattr(
            "os.getenv",
            {
                "PROGRAMFILES": "C:\\Program Files",
                "PROGRAMFILES(X86)": "C:\\Program Files (x86)",
                "LOCALAPPDATA": "C:\\Users\\user\\AppData\\Local",
            }.get,
        )
        assert ChromiumWebbrowser.fallback_paths() == [
            "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
            "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
            "C:\\Program Files\\Microsoft\\Edge Beta\\Application\\msedge.exe",
            "C:\\Program Files (x86)\\Microsoft\\Edge Beta\\Application\\msedge.exe",
            "C:\\Program Files\\Microsoft\\Edge Dev\\Application\\msedge.exe",
            "C:\\Program Files (x86)\\Microsoft\\Edge Dev\\Application\\msedge.exe",
            "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
            "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
            "C:\\Users\\user\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe",
            "C:\\Program Files\\Google\\Chrome Beta\\Application\\chrome.exe",
            "C:\\Program Files (x86)\\Google\\Chrome Beta\\Application\\chrome.exe",
            "C:\\Users\\user\\AppData\\Local\\Google\\Chrome Beta\\Application\\chrome.exe",
            "C:\\Program Files\\Google\\Chrome Canary\\Application\\chrome.exe",
            "C:\\Program Files (x86)\\Google\\Chrome Canary\\Application\\chrome.exe",
            "C:\\Users\\user\\AppData\\Local\\Google\\Chrome Canary\\Application\\chrome.exe",
        ]

    def test_darwin(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("streamlink.webbrowser.chromium.is_win32", False)
        monkeypatch.setattr("streamlink.webbrowser.chromium.is_darwin", True)
        monkeypatch.setattr("streamlink.webbrowser.chromium.Path", PurePosixPath)
        PurePosixPath.home = lambda: PurePosixPath("/Users/user")  # type: ignore[attr-defined]
        assert ChromiumWebbrowser.fallback_paths() == [
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
            "/Users/user/Applications/Chromium.app/Contents/MacOS/Chromium",
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Users/user/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        ]

    def test_other(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("streamlink.webbrowser.chromium.is_win32", False)
        monkeypatch.setattr("streamlink.webbrowser.chromium.is_darwin", False)
        assert ChromiumWebbrowser.fallback_paths() == []


def test_default_args():
    webbrowser = ChromiumWebbrowser()
    assert "--password-store=basic" in webbrowser.arguments
    assert "--use-mock-keychain" in webbrowser.arguments
    assert "--headless=new" not in webbrowser.arguments
    assert not any(arg.startswith("--remote-debugging-host") for arg in webbrowser.arguments)
    assert not any(arg.startswith("--remote-debugging-port") for arg in webbrowser.arguments)
    assert not any(arg.startswith("--user-data-dir") for arg in webbrowser.arguments)


@pytest.mark.trio()
@pytest.mark.parametrize("host", [pytest.param("127.0.0.1", id="ipv4"), pytest.param("::1", id="ipv6")])
@pytest.mark.parametrize("port", [pytest.param(None, id="default-port"), pytest.param(1234, id="custom-port")])
@pytest.mark.parametrize("headless", [pytest.param(True, id="headless"), pytest.param(False, id="not-headless")])
async def test_launch(
    monkeypatch: pytest.MonkeyPatch,
    mock_clock,
    webbrowser_launch,
    host: str,
    port: int | None,
    headless: bool,
):
    async def fake_find_free_port(_):
        await trio.lowlevel.checkpoint()
        return 1234

    monkeypatch.setattr("streamlink.webbrowser.chromium.find_free_port_ipv4", fake_find_free_port)
    monkeypatch.setattr("streamlink.webbrowser.chromium.find_free_port_ipv6", fake_find_free_port)

    webbrowser = ChromiumWebbrowser(host=host, port=port)

    process: trio.Process
    async with webbrowser_launch(webbrowser=webbrowser, headless=headless, timeout=999) as (_nursery, process):
        assert process.poll() is None, "process is still running"
        assert f"--remote-debugging-host={host}" in process.args
        assert "--remote-debugging-port=1234" in process.args
        assert ("--headless=new" in process.args) is headless
        param_user_data_dir = next(  # pragma: no branch
            (arg for arg in process.args if arg.startswith("--user-data-dir=")),
            None,
        )
        assert param_user_data_dir is not None

        user_data_dir = Path(param_user_data_dir[len("--user-data-dir=") :])
        assert user_data_dir.exists()

        # turn the 0.5s sleep() call at the end into a 0.5ms sleep() call
        # autojump_clock=0 would trigger the process's kill() fallback immediately and raise a warning
        mock_clock.rate = 1000

    assert process.poll() == (1 if is_win32 else -SIGTERM), "Process has been terminated"
    assert not user_data_dir.exists()


@pytest.mark.parametrize(
    ("host", "port", "address"),
    [
        pytest.param("127.0.0.1", 1234, "http://127.0.0.1:1234/json/version", id="IPv4"),
        pytest.param("::1", 1234, "http://[::1]:1234/json/version", id="IPv6"),
    ],
)
@pytest.mark.parametrize(
    "session",
    [
        pytest.param({"http-proxy": "http://localhost:4321/"}, id="with-proxy"),
        pytest.param({}, id="without-proxy"),
    ],
    indirect=True,
)
@pytest.mark.parametrize(
    ("num", "raises"),
    [
        pytest.param(10, nullcontext(), id="Success"),
        pytest.param(11, pytest.raises(PluginError), id="Timeout/Failure"),
    ],
)
def test_get_websocket_address(
    monkeypatch: pytest.MonkeyPatch,
    requests_mock: rm.Mocker,
    session: Streamlink,
    host: str,
    port: int,
    address: str,
    num: int,
    raises: nullcontext,
):
    monkeypatch.setattr("time.sleep", lambda _: None)
    hostaddr = f"[{host}]" if ":" in host else host

    payload = {
        "Browser": "Chrome/114.0.5735.133",
        "Protocol-Version": "1.3",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        "V8-Version": "11.4.183.23",
        "WebKit-Version": "537.36 (@fbfa2ce68d01b2201d8c667c2e73f648a61c4f4a)",
        "webSocketDebuggerUrl": f"ws://{hostaddr}:{port}/devtools/browser/some-uuid4",
    }

    responses: list[dict[str, Any]] = [{"exc": Timeout()} for _ in range(num)]
    responses.append({"json": payload})
    mock = requests_mock.register_uri("GET", address, responses)

    webbrowser = ChromiumWebbrowser(host=host, port=port)
    with raises:
        assert webbrowser.get_websocket_url(session) == f"ws://{hostaddr}:{port}/devtools/browser/some-uuid4"
        assert mock.called
        assert mock.last_request
        assert not mock.last_request.proxies.get("http")
