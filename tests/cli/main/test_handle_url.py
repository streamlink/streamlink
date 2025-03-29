from __future__ import annotations

import json
import re
from typing import Iterator
from unittest.mock import Mock

import pytest

import streamlink_cli.main
from streamlink.exceptions import FatalPluginError, PluginError
from streamlink.plugin import Plugin, pluginmatcher
from streamlink.session import Streamlink
from streamlink.stream.stream import Stream


STREAMS = {
    "audio": "mock://stream/audio",
    "720p": "mock://stream/720p",
    "1080p": "mock://stream/1080p",
    "worst": "mock://stream/720p",
    "best": "mock://stream/1080p",
}
STREAMS_MULTIVARIANT = "mock://stream"


class FakeStream(Stream):
    __shortname__ = "fake"

    def __init__(self, session: Streamlink, url: str | None, manifest_url: str | None):
        super().__init__(session)
        self.url = url
        self.manifest_url = manifest_url

    def __json__(self):  # noqa: PLW3201
        return {
            "type": self.__shortname__,
            "url": self.url,
            "manifest_url": self.manifest_url,
        }

    def to_url(self):
        return self.url if self.url else super().to_url()

    def to_manifest_url(self):
        return self.manifest_url if self.manifest_url else super().to_url()


@pytest.fixture(autouse=True)
def _stream_output(monkeypatch: pytest.MonkeyPatch):
    mock_output_stream = Mock()
    mock_output_stream_http = Mock()
    mock_output_stream_passthrough = Mock()
    monkeypatch.setattr(streamlink_cli.main, "output_stream", mock_output_stream)
    monkeypatch.setattr(streamlink_cli.main, "output_stream_http", mock_output_stream_http)
    monkeypatch.setattr(streamlink_cli.main, "output_stream_passthrough", mock_output_stream_passthrough)


@pytest.fixture(autouse=True)
def streams(request: pytest.FixtureRequest, session: Streamlink):
    params = getattr(request, "param", [{}])
    params = params if isinstance(params, list) else [params]

    def streams_generator():
        for param in params:
            if exc := param.get("exc"):
                yield exc
                continue

            streams = param.get("streams", {})
            to_url = param.get("to_url", True)
            to_manifest_url = param.get("to_manifest_url", True)

            yield {
                name: FakeStream(
                    session,
                    url=url if to_url else None,
                    manifest_url=STREAMS_MULTIVARIANT if to_manifest_url else None,
                )
                for name, url in (STREAMS if streams is True else streams).items()
            }

    return streams_generator()


@pytest.fixture(autouse=True)
def plugin(session: Streamlink, streams: Iterator[dict[str, FakeStream]]):
    @pluginmatcher(re.compile(r"https?://plugin"))
    class FakePlugin(Plugin):
        __module__ = "streamlink.plugins.plugin"

        id = "ID"
        author = "AUTHOR"
        category = "CATEGORY"
        title = "TITLE"

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.logger.info("plugin log message")

        def _get_streams(self):
            item = next(streams, None)
            if isinstance(item, BaseException):
                raise item

            return item

    session.plugins.update({"plugin": FakePlugin})


@pytest.mark.parametrize(
    ("argv", "streams", "exit_code", "stdout"),
    [
        pytest.param(
            ["doesnotexist"],
            {},
            1,
            "error: No plugin can handle URL: doesnotexist\n",
            id="no-plugin",
        ),
        pytest.param(
            ["plugin"],
            {"exc": PluginError("Error while fetching streams")},
            1,
            (
                "[cli][info] Found matching plugin plugin for URL plugin\n"
                + "[plugins.plugin][info] plugin log message\n"
                + "error: Error while fetching streams\n"
            ),
            id="fetch-streams-exception",
        ),
        pytest.param(
            ["plugin"],
            {},
            1,
            (
                "[cli][info] Found matching plugin plugin for URL plugin\n"
                + "[plugins.plugin][info] plugin log message\n"
                + "error: No playable streams found on this URL: plugin\n"
            ),
            id="no-streams",
        ),
        pytest.param(
            ["plugin"],
            {"streams": True},
            0,
            (
                "[cli][info] Found matching plugin plugin for URL plugin\n"
                + "[plugins.plugin][info] plugin log message\n"
                + "Available streams: audio, 720p (worst), 1080p (best)\n"
            ),
            id="streams-selection-none",
        ),
        pytest.param(
            ["plugin", "one,two,three"],
            {"streams": True},
            1,
            (
                "[cli][info] Found matching plugin plugin for URL plugin\n"
                + "[plugins.plugin][info] plugin log message\n"
                + "error: The specified stream(s) 'one, two, three' could not be found.\n"
                + "       Available streams: audio, 720p (worst), 1080p (best)\n"
            ),
            id="streams-selection-invalid",
        ),
        pytest.param(
            ["plugin", "best"],
            {"streams": True},
            0,
            (
                "[cli][info] Found matching plugin plugin for URL plugin\n"
                + "[plugins.plugin][info] plugin log message\n"
                + "[cli][info] Available streams: audio, 720p (worst), 1080p (best)\n"
                + "[cli][info] Opening stream: 1080p (fake)\n"
            ),
            id="streams-selection-best",
        ),
        pytest.param(
            ["--stream-url", "plugin"],
            {"streams": True},
            0,
            f"{STREAMS_MULTIVARIANT}\n",
            id="stream-url-selection-none",
        ),
        pytest.param(
            ["--stream-url", "plugin"],
            {"streams": True, "to_manifest_url": False},
            1,
            "error: The stream specified cannot be translated to a URL\n",
            id="stream-url-selection-none-no-multivariant",
        ),
        pytest.param(
            ["--stream-url", "plugin", "best"],
            {"streams": True},
            0,
            f"{STREAMS['best']}\n",
            id="stream-url-selection-best",
        ),
        pytest.param(
            ["--stream-url", "plugin", "best"],
            {"streams": True, "to_url": False},
            1,
            "error: The stream specified cannot be translated to a URL\n",
            id="stream-url-selection-best-no-url",
        ),
        pytest.param(
            ["--json", "plugin"],
            {"streams": True},
            0,
            json.dumps(
                {
                    "plugin": "plugin",
                    "metadata": {
                        "id": "ID",
                        "author": "AUTHOR",
                        "category": "CATEGORY",
                        "title": "TITLE",
                    },
                    "streams": {
                        "audio": {
                            "type": "fake",
                            "url": "mock://stream/audio",
                            "manifest_url": "mock://stream",
                        },
                        "worst": {
                            "type": "fake",
                            "url": "mock://stream/720p",
                            "manifest_url": "mock://stream",
                        },
                        "best": {
                            "type": "fake",
                            "url": "mock://stream/1080p",
                            "manifest_url": "mock://stream",
                        },
                        "720p": {
                            "type": "fake",
                            "url": "mock://stream/720p",
                            "manifest_url": "mock://stream",
                        },
                        "1080p": {
                            "type": "fake",
                            "url": "mock://stream/1080p",
                            "manifest_url": "mock://stream",
                        },
                    },
                },
                indent=2,
                separators=(",", ": "),
            )
            + "\n",
            id="json-selection-none",
        ),
        pytest.param(
            ["--json", "plugin", "one,two,three"],
            {"streams": True},
            1,
            json.dumps(
                {
                    "plugin": "plugin",
                    "metadata": {
                        "id": "ID",
                        "author": "AUTHOR",
                        "category": "CATEGORY",
                        "title": "TITLE",
                    },
                    "streams": {
                        "audio": {
                            "type": "fake",
                            "url": "mock://stream/audio",
                            "manifest_url": "mock://stream",
                        },
                        "worst": {
                            "type": "fake",
                            "url": "mock://stream/720p",
                            "manifest_url": "mock://stream",
                        },
                        "best": {
                            "type": "fake",
                            "url": "mock://stream/1080p",
                            "manifest_url": "mock://stream",
                        },
                        "720p": {
                            "type": "fake",
                            "url": "mock://stream/720p",
                            "manifest_url": "mock://stream",
                        },
                        "1080p": {
                            "type": "fake",
                            "url": "mock://stream/1080p",
                            "manifest_url": "mock://stream",
                        },
                    },
                    "error": "The specified stream(s) 'one, two, three' could not be found",
                },
                indent=2,
                separators=(",", ": "),
            )
            + "\n",
            id="json-selection-invalid",
        ),
        pytest.param(
            ["--json", "plugin", "best"],
            {"streams": True},
            0,
            json.dumps(
                {
                    "type": "fake",
                    "url": "mock://stream/1080p",
                    "manifest_url": "mock://stream",
                    "metadata": {
                        "id": "ID",
                        "author": "AUTHOR",
                        "category": "CATEGORY",
                        "title": "TITLE",
                    },
                },
                indent=2,
                separators=(",", ": "),
            )
            + "\n",
            id="json-selection-best",
        ),
    ],
    indirect=["argv", "streams"],
)
def test_handle_url_text_output(
    capsys: pytest.CaptureFixture[str],
    argv: list,
    streams: Iterator[dict[str, FakeStream]],
    exit_code: int,
    stdout: str,
):
    with pytest.raises(SystemExit) as exc_info:
        streamlink_cli.main.main()

    assert exc_info.value.code == exit_code
    out, err = capsys.readouterr()
    assert out == stdout
    assert err == ""


@pytest.mark.parametrize(
    ("argv", "streams", "exit_code", "retries", "stdout"),
    [
        pytest.param(
            ["plugin", "best"],
            [],
            1,
            0,
            (
                "[cli][info] Found matching plugin plugin for URL plugin\n"
                + "[plugins.plugin][info] plugin log message\n"
                + "error: No playable streams found on this URL: plugin\n"
            ),
            id="no-retries-implicit",
        ),
        pytest.param(
            ["plugin", "best", "--retry-streams=0", "--retry-max=0"],
            [],
            1,
            0,
            (
                "[cli][info] Found matching plugin plugin for URL plugin\n"
                + "[plugins.plugin][info] plugin log message\n"
                + "error: No playable streams found on this URL: plugin\n"
            ),
            id="no-retries-explicit",
        ),
        pytest.param(
            ["plugin", "best", "--retry-max=5"],
            [],
            1,
            5,
            (
                "[cli][info] Found matching plugin plugin for URL plugin\n"
                + "[plugins.plugin][info] plugin log message\n"
                + "[cli][info] Waiting for streams, retrying every 1 second(s)\n"
                + "error: No playable streams found on this URL: plugin\n"
            ),
            id="no-streams",
        ),
        pytest.param(
            ["plugin", "best", "--retry-max=5"],
            [{"streams": True}],
            0,
            0,
            (
                "[cli][info] Found matching plugin plugin for URL plugin\n"
                + "[plugins.plugin][info] plugin log message\n"
                + "[cli][info] Available streams: audio, 720p (worst), 1080p (best)\n"
                + "[cli][info] Opening stream: 1080p (fake)\n"
            ),
            id="success-on-first-attempt",
        ),
        pytest.param(
            ["plugin", "best", "--retry-streams=3", "--retry-max=5"],
            [{}, {}, {"streams": True}],
            0,
            2,
            (
                "[cli][info] Found matching plugin plugin for URL plugin\n"
                + "[plugins.plugin][info] plugin log message\n"
                + "[cli][info] Waiting for streams, retrying every 3.0 second(s)\n"
                + "[cli][info] Available streams: audio, 720p (worst), 1080p (best)\n"
                + "[cli][info] Opening stream: 1080p (fake)\n"
            ),
            id="success-on-third-attempt",
        ),
        pytest.param(
            ["plugin", "best", "--retry-streams=3", "--retry-max=5"],
            [{"exc": PluginError("failure")}, {"streams": True}],
            0,
            1,
            (
                "[cli][info] Found matching plugin plugin for URL plugin\n"
                + "[plugins.plugin][info] plugin log message\n"
                + "[cli][error] failure\n"
                + "[cli][info] Waiting for streams, retrying every 3.0 second(s)\n"
                + "[cli][info] Available streams: audio, 720p (worst), 1080p (best)\n"
                + "[cli][info] Opening stream: 1080p (fake)\n"
            ),
            id="success-with-plugin-error-on-first-attempt",
        ),
        pytest.param(
            ["plugin", "best", "--retry-streams=3", "--retry-max=5"],
            [{}, {"exc": PluginError("failure")}, {"streams": True}],
            0,
            2,
            (
                "[cli][info] Found matching plugin plugin for URL plugin\n"
                + "[plugins.plugin][info] plugin log message\n"
                + "[cli][info] Waiting for streams, retrying every 3.0 second(s)\n"
                + "[cli][error] failure\n"
                + "[cli][info] Available streams: audio, 720p (worst), 1080p (best)\n"
                + "[cli][info] Opening stream: 1080p (fake)\n"
            ),
            id="success-with-plugin-error-on-second-attempt",
        ),
        pytest.param(
            ["plugin", "best", "--retry-streams=3"],
            [{} for _ in range(20)] + [{"streams": True}],
            0,
            20,
            (
                "[cli][info] Found matching plugin plugin for URL plugin\n"
                + "[plugins.plugin][info] plugin log message\n"
                + "[cli][info] Waiting for streams, retrying every 3.0 second(s)\n"
                + "[cli][info] Available streams: audio, 720p (worst), 1080p (best)\n"
                + "[cli][info] Opening stream: 1080p (fake)\n"
            ),
            id="success-no-max-attempts",
        ),
        pytest.param(
            ["plugin", "best", "--retry-max=5"],
            [{"exc": FatalPluginError("fatal")}, {"streams": True}],
            1,
            0,
            (
                "[cli][info] Found matching plugin plugin for URL plugin\n"
                + "[plugins.plugin][info] plugin log message\n"
                + "error: fatal\n"
            ),
            id="fatal-plugin-error-on-first-attempt",
        ),
        pytest.param(
            ["plugin", "best", "--retry-max=5"],
            [{}, {"exc": FatalPluginError("fatal")}, {"streams": True}],
            1,
            1,
            (
                "[cli][info] Found matching plugin plugin for URL plugin\n"
                + "[plugins.plugin][info] plugin log message\n"
                + "[cli][info] Waiting for streams, retrying every 1 second(s)\n"
                + "error: fatal\n"
            ),
            id="fatal-plugin-error-on-second-attempt",
        ),
    ],
    indirect=["argv", "streams"],
)  # fmt: skip
def test_handle_url_retry(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    argv: list,
    streams: Iterator[dict[str, FakeStream]],
    exit_code: int,
    retries: int,
    stdout: list[str],
):
    mock_sleep = Mock()
    monkeypatch.setattr("streamlink_cli.main.sleep", mock_sleep)

    with pytest.raises(SystemExit) as exc_info:
        streamlink_cli.main.main()

    assert exc_info.value.code == exit_code
    assert mock_sleep.call_count == retries

    out, err = capsys.readouterr()
    assert out == stdout
    assert err == ""


@pytest.mark.parametrize("argv", [pytest.param(["plugin", "best"], id="argv")], indirect=["argv"])
class TestHandleUrlKeyboardInterruptAndCleanup:
    @pytest.fixture(autouse=True)
    def handle_url(self, request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch):
        mock_handle_url = Mock()
        if getattr(request, "param", False):
            mock_handle_url.side_effect = KeyboardInterrupt
        monkeypatch.setattr(streamlink_cli.main, "handle_url", mock_handle_url)

    @staticmethod
    def _mock(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch, attr: str):
        param = getattr(request, "param", {})
        if not param.get("initialized", False):
            monkeypatch.setattr(streamlink_cli.main, attr, None)
            yield
        else:
            mock = Mock()
            monkeypatch.setattr(streamlink_cli.main, attr, mock)
            if param.get("close_raises", False):
                mock.close.side_effect = KeyboardInterrupt

            yield mock
            assert mock.close.call_count == 1

    @pytest.fixture(autouse=True)
    def output(self, request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch):
        yield from self._mock(request, monkeypatch, "output")

    @pytest.fixture(autouse=True)
    def stream_fd(self, request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch):
        yield from self._mock(request, monkeypatch, "stream_fd")

    @pytest.mark.parametrize(
        ("handle_url", "output", "stream_fd", "exit_code", "stdout"),
        [
            pytest.param(
                False,
                {},
                {},
                0,
                "",
                id="no-keyboardinterrupt",
            ),
            pytest.param(
                True,
                {},
                {},
                130,
                "Interrupted! Exiting...\n",
                id="no-output",
            ),
            pytest.param(
                True,
                {"initialized": True},
                {},
                130,
                "Interrupted! Exiting...\n",
                id="output",
            ),
            pytest.param(
                True,
                {"initialized": True},
                {"initialized": True},
                130,
                "Interrupted! Exiting...\n[cli][info] Closing currently open stream...\n",
                id="output-streamfd",
            ),
            pytest.param(
                True,
                {"initialized": True, "close_raises": True},
                {"initialized": True},
                130,
                "Interrupted! Exiting...\n[cli][info] Closing currently open stream...\n",
                id="output-streamfd-outputclose-interrupted",
            ),
            pytest.param(
                True,
                {"initialized": True},
                {"initialized": True, "close_raises": True},
                130,
                "Interrupted! Exiting...\n[cli][info] Closing currently open stream...\n",
                id="output-streamfd-streamfdclose-interrupted",
            ),
        ],
        indirect=["handle_url", "output", "stream_fd"],
    )
    def test_handle_url(
        self,
        capsys: pytest.CaptureFixture[str],
        argv: list,
        handle_url: None,
        output: Mock,
        stream_fd: Mock,
        exit_code: int,
        stdout: str,
    ):
        # noinspection PyTypeChecker
        with pytest.raises((SystemExit, KeyboardInterrupt)) as exc_info:
            streamlink_cli.main.main()

        assert isinstance(exc_info.value, SystemExit)
        assert exc_info.value.code == exit_code
        out, err = capsys.readouterr()
        assert out == stdout
        assert err == ""
