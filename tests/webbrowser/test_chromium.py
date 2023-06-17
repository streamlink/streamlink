from contextlib import nullcontext
from pathlib import Path, PurePosixPath, PureWindowsPath
from signal import SIGTERM
from typing import Any, Dict, List

import pytest
import requests_mock as rm
import trio
from requests import Timeout

from streamlink.compat import is_win32
from streamlink.exceptions import PluginError
from streamlink.session import Streamlink
from streamlink.webbrowser.chromium import ChromiumWebbrowser


class TestFallbacks:
    def test_win32(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("streamlink.webbrowser.chromium.is_win32", True)
        monkeypatch.setattr("streamlink.webbrowser.chromium.is_darwin", False)
        monkeypatch.setattr("streamlink.webbrowser.chromium.Path", PureWindowsPath)
        monkeypatch.setattr("os.getenv", {
            "PROGRAMFILES": "C:\\Program Files",
            "PROGRAMFILES(X86)": "C:\\Program Files (x86)",
            "LOCALAPPDATA": "C:\\Users\\user\\AppData\\Local",
        }.get)
        assert ChromiumWebbrowser.fallback_paths() == [
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


class TestLaunchArgs:
    def test_launch_args(self):
        webbrowser = ChromiumWebbrowser()
        assert "--password-store=basic" in webbrowser.arguments
        assert "--use-mock-keychain" in webbrowser.arguments
        assert "--headless=new" in webbrowser.arguments
        assert not any(arg.startswith("--remote-debugging-host") for arg in webbrowser.arguments)
        assert not any(arg.startswith("--remote-debugging-port") for arg in webbrowser.arguments)
        assert not any(arg.startswith("--user-data-dir") for arg in webbrowser.arguments)

    @pytest.mark.parametrize("headless", [True, False])
    def test_headless(self, headless: bool):
        webbrowser = ChromiumWebbrowser(headless=headless)
        assert ("--headless=new" in webbrowser.arguments) is headless


@pytest.mark.trio()
@pytest.mark.parametrize("host", ["127.0.0.1", "::1"])
@pytest.mark.parametrize("port", [None, 1234])
async def test_launch(monkeypatch: pytest.MonkeyPatch, mock_clock, webbrowser_launch, host, port):
    async def fake_find_free_port(_):
        return 1234

    monkeypatch.setattr("streamlink.webbrowser.chromium.find_free_port_ipv4", fake_find_free_port)
    monkeypatch.setattr("streamlink.webbrowser.chromium.find_free_port_ipv6", fake_find_free_port)

    webbrowser = ChromiumWebbrowser(host=host, port=port)

    nursery: trio.Nursery
    process: trio.Process
    async with webbrowser_launch(webbrowser=webbrowser, timeout=999) as (nursery, process):  # noqa: F841
        assert process.poll() is None, "process is still running"
        assert f"--remote-debugging-host={host}" in process.args
        assert "--remote-debugging-port=1234" in process.args
        param_user_data_dir = next(  # pragma: no branch
            (arg for arg in process.args if arg.startswith("--user-data-dir=")),
            None,
        )
        assert param_user_data_dir is not None

        user_data_dir = Path(param_user_data_dir[len("--user-data-dir="):])
        assert user_data_dir.exists()

        # turn the 0.5s sleep() call at the end into a 0.5ms sleep() call
        # autojump_clock=0 would trigger the process's kill() fallback immediately and raise a warning
        mock_clock.rate = 1000

    assert process.poll() == (1 if is_win32 else -SIGTERM), "Process has been terminated"
    assert not user_data_dir.exists()


@pytest.mark.parametrize(("host", "port"), [
    pytest.param("127.0.0.1", 1234, id="IPv4"),
    pytest.param("::1", 1234, id="IPv6"),
])
@pytest.mark.parametrize(("num", "raises"), [
    pytest.param(10, nullcontext(), id="Success"),
    pytest.param(11, pytest.raises(PluginError), id="Timeout/Failure"),
])
def test_get_websocket_address(
    monkeypatch: pytest.MonkeyPatch,
    requests_mock: rm.Mocker,
    session: Streamlink,
    host: str,
    port: int,
    num: int,
    raises: nullcontext,
):
    monkeypatch.setattr("time.sleep", lambda _: None)

    payload = {
      "Browser": "Chrome/114.0.5735.133",
      "Protocol-Version": "1.3",
      "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
      "V8-Version": "11.4.183.23",
      "WebKit-Version": "537.36 (@fbfa2ce68d01b2201d8c667c2e73f648a61c4f4a)",
      "webSocketDebuggerUrl": f"ws://{host}:{port}/devtools/browser/some-uuid4",
    }

    for address in ("http://127.0.0.1:1234/json/version", "http://[::1]:1234/json/version"):
        responses: List[Dict[str, Any]] = [{"exc": Timeout()} for _ in range(num)]
        responses.append({"json": payload})
        requests_mock.register_uri("GET", address, responses)

    webbrowser = ChromiumWebbrowser(host=host, port=port)
    with raises:
        assert webbrowser.get_websocket_url(session) == f"ws://{host}:{port}/devtools/browser/some-uuid4"
