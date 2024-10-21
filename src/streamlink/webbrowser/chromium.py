from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

import trio

import streamlink.validate as validate
from streamlink.compat import is_darwin, is_win32
from streamlink.session import Streamlink
from streamlink.utils.socket import find_free_port_ipv4, find_free_port_ipv6
from streamlink.webbrowser.webbrowser import Webbrowser


class ChromiumWebbrowser(Webbrowser):
    ERROR_RESOLVE = "Could not find Chromium-based web browser executable"

    @classmethod
    def names(cls) -> list[str]:
        return [
            "chromium",
            "chromium-browser",
            "chrome",
            "google-chrome",
            "google-chrome-stable",
        ]

    @classmethod
    def fallback_paths(cls) -> list[str | Path]:
        if is_win32:
            ms_edge: list[str | Path] = [
                str(Path(base) / sub / "msedge.exe")
                for sub in (
                    "Microsoft\\Edge\\Application",
                    "Microsoft\\Edge Beta\\Application",
                    "Microsoft\\Edge Dev\\Application",
                )
                for base in [
                    os.getenv(env)
                    for env in (
                        "PROGRAMFILES",
                        "PROGRAMFILES(X86)",
                    )
                ]
                if base is not None
            ]
            google_chrome: list[str | Path] = [
                str(Path(base) / sub / "chrome.exe")
                for sub in (
                    "Google\\Chrome\\Application",
                    "Google\\Chrome Beta\\Application",
                    "Google\\Chrome Canary\\Application",
                )
                for base in [
                    os.getenv(env)
                    for env in (
                        "PROGRAMFILES",
                        "PROGRAMFILES(X86)",
                        "LOCALAPPDATA",
                    )
                ]
                if base is not None
            ]
            return ms_edge + google_chrome

        if is_darwin:
            return [
                "/Applications/Chromium.app/Contents/MacOS/Chromium",
                str(Path.home() / "Applications/Chromium.app/Contents/MacOS/Chromium"),
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                str(Path.home() / "Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            ]

        return []

    @classmethod
    def launch_args(cls) -> list[str]:
        # https://docs.google.com/spreadsheets/d/1n-vw_PCPS45jX3Jt9jQaAhFqBY6Ge1vWF_Pa0k7dCk4
        # https://peter.sh/experiments/chromium-command-line-switches/
        return [
            # Don't auto-play videos
            "--autoplay-policy=user-gesture-required",
            # Suppress all permission prompts by automatically denying them
            "--deny-permission-prompts",
            # Disable various background network services, including
            #   extension updating, safe browsing service, upgrade detector, translate, UMA
            "--disable-background-networking",
            # Chromium treats "foreground" tabs as "backgrounded" if the surrounding window is occluded by another window
            "--disable-backgrounding-occluded-windows",
            # Disable crashdump collection (reporting is already disabled in Chromium)
            "--disable-breakpad",
            # Disables client-side phishing detection
            "--disable-client-side-phishing-detection",
            # Disable some built-in extensions that aren't affected by `--disable-extensions`
            "--disable-component-extensions-with-background-pages",
            # Don't update the browser 'components' listed at chrome://components/
            "--disable-component-update",
            # Disable installation of default apps
            "--disable-default-apps",
            # Disable all chrome extensions
            "--disable-extensions",
            # Hide toolbar button that opens dialog for controlling media sessions
            "--disable-features=GlobalMediaControls",
            # Disable the "Chrome Media Router" which creates some background network activity to discover castable targets
            "--disable-features=MediaRouter",
            # Disables Chrome translation, both the manual option and the popup prompt
            "--disable-features=Translate",
            # Suppresses hang monitor dialogs in renderer processes
            #   This flag may allow slow unload handlers on a page to prevent the tab from closing
            "--disable-hang-monitor",
            # Disables logging
            "--disable-logging",
            # Disables the Web Notification and the Push APIs
            "--disable-notifications",
            # Disable popup blocking. `--block-new-web-contents` is the strict version of this
            "--disable-popup-blocking",
            # Reloading a page that came from a POST normally prompts the user
            "--disable-prompt-on-repost",
            # Disable syncing with Google
            "--disable-sync",
            # Forces the maximum disk space to be used by the disk cache, in bytes
            "--disk-cache-size=0",
            # Disable reporting to UMA, but allows for collection
            "--metrics-recording-only",
            # Mute any audio
            "--mute-audio",
            # Disable the default browser check, do not prompt to set it as such
            "--no-default-browser-check",
            # Disables all experiments set on about:flags
            "--no-experiments",
            # Skip first run wizards
            "--no-first-run",
            # Disables the service process from adding itself as an autorun process
            #   This does not delete existing autorun registrations, it just prevents the service from registering a new one
            "--no-service-autorun",
            # Avoid potential instability of using Gnome Keyring or KDE wallet
            "--password-store=basic",
            # No initial CDP target (no empty default tab)
            "--silent-launch",
            # Use mock keychain on Mac to prevent the blocking permissions dialog asking:
            #   Do you want the application "Chromium.app" to accept incoming network connections?
            "--use-mock-keychain",
            # When not using headless mode, try to disrupt the user as little as possible
            "--window-size=0,0",
        ]

    def __init__(
        self,
        *args,
        host: str | None = None,
        port: int | None = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.host = host or "127.0.0.1"
        self.port = port

    @asynccontextmanager
    async def launch(self, headless: bool = False, timeout: float | None = None) -> AsyncGenerator[trio.Nursery, None]:
        if self.port is None:
            if ":" in self.host:
                self.port = await find_free_port_ipv6(self.host)
            else:
                self.port = await find_free_port_ipv4(self.host)

        # no async rmtree
        with self._create_temp_dir() as user_data_dir:
            arguments = self.arguments.copy()
            if headless:
                arguments.append("--headless=new")
            arguments.extend([
                f"--remote-debugging-host={self.host}",
                f"--remote-debugging-port={self.port}",
                f"--user-data-dir={user_data_dir}",
            ])

            async with super()._launch(self.executable, arguments, headless=headless, timeout=timeout) as nursery:
                yield nursery

            # Even though we've awaited the process termination in the async generator above,
            # the rmtree() call of the temp-dir's context manager can sometimes still fail.
            # This is probably caused by filesystem commits of the OS, not sure,
            # but we have to wait a bit in order to be able to gracefully remove the temp user data dir.
            # A terrible solution to use a static timer :(
            await trio.sleep(0.5)

    def get_websocket_url(self, session: Streamlink) -> str:
        return session.http.get(
            f"http://{f'[{self.host}]' if ':' in self.host else self.host}:{self.port}/json/version",
            retries=10,
            retry_backoff=0.25,
            retry_max_backoff=0.25,
            timeout=0.1,
            proxies={
                "http": "",
            },
            schema=validate.Schema(
                validate.parse_json(),
                {"webSocketDebuggerUrl": validate.url(scheme="ws")},
                validate.get("webSocketDebuggerUrl"),
            ),
        )
