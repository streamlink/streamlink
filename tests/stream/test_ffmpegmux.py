from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING
from unittest.mock import Mock, call

import pytest

from streamlink.stream.ffmpegmux import FFMPEGMuxer, FFmpegVersionOutput


if TYPE_CHECKING:
    from streamlink import Streamlink


# noinspection PyProtectedMember
@pytest.fixture(autouse=True)
def _resolve_command_cache_clear():
    FFMPEGMuxer._resolve_command.cache_clear()
    yield
    FFMPEGMuxer._resolve_command.cache_clear()


@pytest.fixture(autouse=True)
def _logger(caplog: pytest.LogCaptureFixture):
    caplog.set_level(1, "streamlink")


@pytest.fixture()
def session(session: Streamlink):
    session.set_option("ffmpeg-no-validation", True)

    return session


class TestCommand:
    def test_cache(self, monkeypatch: pytest.MonkeyPatch, session: Streamlink):
        mock = Mock()
        monkeypatch.setattr("streamlink.stream.ffmpegmux.which", mock)

        mock.return_value = "some_value"
        assert FFMPEGMuxer.command(session) == "some_value"
        assert FFMPEGMuxer.command(session) == "some_value"
        assert len(mock.call_args_list) == 1

        mock.reset_mock()

        mock.return_value = "other_value"
        assert FFMPEGMuxer.command(session) == "some_value"
        assert len(mock.call_args_list) == 0

    @pytest.mark.parametrize(
        ("command", "which", "expected"),
        [
            pytest.param(None, {"ffmpeg": None}, None, id="resolver-negative"),
            pytest.param(None, {"ffmpeg": "ffmpeg"}, "ffmpeg", id="resolver-posix"),
            pytest.param(None, {"ffmpeg": "ffmpeg.exe"}, "ffmpeg.exe", id="resolver-windows"),
            pytest.param("custom", {"ffmpeg": "ffmpeg"}, None, id="custom-negative"),
            pytest.param("custom", {"ffmpeg": "ffmpeg", "custom": "custom"}, "custom", id="custom-positive"),
        ],
    )
    def test_no_cache(
        self,
        monkeypatch: pytest.MonkeyPatch,
        session: Streamlink,
        command: str | None,
        which: dict,
        expected: str | None,
    ):
        monkeypatch.setattr("streamlink.stream.ffmpegmux.which", Mock(side_effect=which.get))
        session.options.update({"ffmpeg-ffmpeg": command})
        assert FFMPEGMuxer.command(session) == expected

    @pytest.mark.parametrize(
        ("resolved", "expected"),
        [
            pytest.param(None, False, id="negative"),
            pytest.param("ffmpeg", True, id="positive"),
        ],
    )
    def test_is_usable(self, monkeypatch: pytest.MonkeyPatch, session: Streamlink, resolved: str | None, expected: bool):
        monkeypatch.setattr("streamlink.stream.ffmpegmux.which", Mock(return_value=resolved))
        assert FFMPEGMuxer.is_usable(session) is expected

    def test_log(self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, session: Streamlink):
        monkeypatch.setattr("streamlink.stream.ffmpegmux.which", Mock(return_value=None))

        assert not FFMPEGMuxer.is_usable(session)
        assert [(record.module, record.levelname, record.message) for record in caplog.records] == [
            (
                "ffmpegmux",
                "warning",
                "No valid FFmpeg binary was found. See the --ffmpeg-ffmpeg option.",
            ),
            (
                "ffmpegmux",
                "warning",
                "Muxing streams is unsupported! Only a subset of the available streams can be returned!",
            ),
        ]

        caplog.records.clear()
        assert not FFMPEGMuxer.is_usable(session)
        assert len(caplog.records) == 0

    def test_no_log(self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, session: Streamlink):
        monkeypatch.setattr("streamlink.stream.ffmpegmux.which", Mock(return_value="foo"))
        assert FFMPEGMuxer.is_usable(session)
        assert len(caplog.records) == 0

    def test_validate_success(self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, session: Streamlink):
        session.options.update({"ffmpeg-no-validation": False})

        class MyFFmpegVersionOutput(FFmpegVersionOutput):
            def run(self):
                self.onstdout(0, "ffmpeg version 0.0.0 suffix")
                self.onstdout(1, "foo")
                self.onstdout(2, "bar")
                return True

        mock_versionoutput = Mock(side_effect=MyFFmpegVersionOutput)
        monkeypatch.setattr("streamlink.stream.ffmpegmux.which", Mock(return_value="/usr/bin/ffmpeg"))
        monkeypatch.setattr("streamlink.stream.ffmpegmux.FFmpegVersionOutput", mock_versionoutput)

        result = FFMPEGMuxer.command(session)
        assert result == "/usr/bin/ffmpeg"
        assert mock_versionoutput.call_args_list == [
            call(["/usr/bin/ffmpeg", "-version"], timeout=4.0),
        ]
        assert [(record.module, record.levelname, record.message) for record in caplog.records] == [
            ("ffmpegmux", "trace", "Querying FFmpeg version: ['/usr/bin/ffmpeg', '-version']"),
            ("ffmpegmux", "debug", "ffmpeg version 0.0.0 suffix"),
            ("ffmpegmux", "debug", " foo"),
            ("ffmpegmux", "debug", " bar"),
        ]

    @pytest.mark.parametrize(
        ("timeout_value", "expected_timeout"),
        [
            pytest.param(None, 4.0, id="default"),
            pytest.param(9.5, 9.5, id="custom"),
        ],
    )
    def test_validate_timeout(self, monkeypatch: pytest.MonkeyPatch, session: Streamlink, timeout_value, expected_timeout):
        session.options.update({
            "ffmpeg-no-validation": False,
            "ffmpeg-validation-timeout": timeout_value,
        })

        class MyFFmpegVersionOutput(FFmpegVersionOutput):
            def run(self):
                self.onstdout(0, "ffmpeg version 0.0.0 custom")
                return True

        mock_versionoutput = Mock(side_effect=MyFFmpegVersionOutput)
        monkeypatch.setattr("streamlink.stream.ffmpegmux.which", Mock(return_value="/usr/bin/ffmpeg"))
        monkeypatch.setattr("streamlink.stream.ffmpegmux.FFmpegVersionOutput", mock_versionoutput)

        result = FFMPEGMuxer.command(session)
        assert result == "/usr/bin/ffmpeg"
        assert mock_versionoutput.call_args_list == [
            call(["/usr/bin/ffmpeg", "-version"], timeout=expected_timeout),
        ]

    def test_validate_failure(self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, session: Streamlink):
        session.options.update({"ffmpeg-no-validation": False})

        class MyFFmpegVersionOutput(FFmpegVersionOutput):
            def run(self):
                return False

        mock_versionoutput = Mock(side_effect=MyFFmpegVersionOutput)
        monkeypatch.setattr("streamlink.stream.ffmpegmux.which", Mock(return_value="/usr/bin/ffmpeg"))
        monkeypatch.setattr("streamlink.stream.ffmpegmux.FFmpegVersionOutput", mock_versionoutput)

        result = FFMPEGMuxer.command(session)
        assert result is None
        assert mock_versionoutput.call_args_list == [
            call(["/usr/bin/ffmpeg", "-version"], timeout=4.0),
        ]
        assert [(record.module, record.levelname, record.message) for record in caplog.records] == [
            ("ffmpegmux", "trace", "Querying FFmpeg version: ['/usr/bin/ffmpeg', '-version']"),
            ("ffmpegmux", "error", "Could not validate FFmpeg!"),
            ("ffmpegmux", "error", "Unexpected FFmpeg version output while running ['/usr/bin/ffmpeg', '-version']"),
            ("ffmpegmux", "warning", "No valid FFmpeg binary was found. See the --ffmpeg-ffmpeg option."),
            ("ffmpegmux", "warning", "Muxing streams is unsupported! Only a subset of the available streams can be returned!"),
        ]


class TestFFmpegVersionOutput:
    @pytest.fixture()
    def output(self):
        output = FFmpegVersionOutput(["/usr/bin/ffmpeg", "-version"], timeout=1.0)
        assert output.command == ["/usr/bin/ffmpeg", "-version"]
        assert output.timeout == 1.0  # noqa: RUF069
        assert output.output == []
        assert output.version is None

        return output

    def test_success(self, output: FFmpegVersionOutput):
        output.onstdout(0, "ffmpeg version 0.0.0 suffix")
        assert output.output == ["ffmpeg version 0.0.0 suffix"]
        assert output.version == "0.0.0"

        output.onstdout(1, "foo")
        output.onstdout(2, "bar")
        assert output.output == ["ffmpeg version 0.0.0 suffix", "foo", "bar"]
        assert output.version == "0.0.0"

        assert output.onexit(0)

    def test_failure_stdout(self, output: FFmpegVersionOutput):
        output.onstdout(0, "invalid")
        assert output.output == []
        assert output.version is None
        assert not output.onexit(0)

    def test_failure_exitcode(self, output: FFmpegVersionOutput):
        output.onstdout(0, "ffmpeg version 0.0.0 suffix")
        assert output.output == ["ffmpeg version 0.0.0 suffix"]
        assert output.version == "0.0.0"
        assert not output.onexit(1)


class TestOpen:
    FFMPEG_ARGS_DEFAULT_BASE = ["-y", "-nostats"]
    FFMPEG_ARGS_DEFAULT_LOGLEVEL = ["-loglevel", "info"]
    FFMPEG_ARGS_DEFAULT_CODECS = ["-c:v", FFMPEGMuxer.DEFAULT_VIDEO_CODEC, "-c:a", FFMPEGMuxer.DEFAULT_AUDIO_CODEC]
    FFMPEG_ARGS_DEFAULT_FORMAT = ["-f", FFMPEGMuxer.DEFAULT_OUTPUT_FORMAT]
    FFMPEG_ARGS_DEFAULT_OUTPUT = ["pipe:1"]

    @pytest.fixture(autouse=True)
    def which(self, monkeypatch: pytest.MonkeyPatch):
        mock = Mock(return_value="ffmpeg")
        monkeypatch.setattr("streamlink.stream.ffmpegmux.which", mock)

        return mock

    @pytest.fixture()
    def popen(self, monkeypatch: pytest.MonkeyPatch):
        mock = Mock()
        monkeypatch.setattr("subprocess.Popen", mock)

        return mock

    @pytest.mark.parametrize(
        ("options", "muxer_args", "expected"),
        [
            pytest.param(
                {},
                {},
                [
                    *FFMPEG_ARGS_DEFAULT_BASE,
                    *FFMPEG_ARGS_DEFAULT_LOGLEVEL,
                    *FFMPEG_ARGS_DEFAULT_CODECS,
                    *FFMPEG_ARGS_DEFAULT_FORMAT,
                    *FFMPEG_ARGS_DEFAULT_OUTPUT,
                ],
                id="default",
            ),
            pytest.param(
                {},
                {"loglevel": "verbose"},
                [
                    *FFMPEG_ARGS_DEFAULT_BASE,
                    "-loglevel",
                    "verbose",
                    *FFMPEG_ARGS_DEFAULT_CODECS,
                    *FFMPEG_ARGS_DEFAULT_FORMAT,
                    *FFMPEG_ARGS_DEFAULT_OUTPUT,
                ],
                id="loglevel",
            ),
            pytest.param(
                {"ffmpeg-loglevel": "error"},
                {"loglevel": "verbose"},
                [
                    *FFMPEG_ARGS_DEFAULT_BASE,
                    "-loglevel",
                    "error",
                    *FFMPEG_ARGS_DEFAULT_CODECS,
                    *FFMPEG_ARGS_DEFAULT_FORMAT,
                    *FFMPEG_ARGS_DEFAULT_OUTPUT,
                ],
                id="loglevel-user-override",
            ),
            pytest.param(
                {},
                {"format": "mpegts"},
                [
                    *FFMPEG_ARGS_DEFAULT_BASE,
                    *FFMPEG_ARGS_DEFAULT_LOGLEVEL,
                    *FFMPEG_ARGS_DEFAULT_CODECS,
                    "-f",
                    "mpegts",
                    *FFMPEG_ARGS_DEFAULT_OUTPUT,
                ],
                id="format",
            ),
            pytest.param(
                {"ffmpeg-fout": "avi"},
                {"format": "mpegts"},
                [
                    *FFMPEG_ARGS_DEFAULT_BASE,
                    *FFMPEG_ARGS_DEFAULT_LOGLEVEL,
                    *FFMPEG_ARGS_DEFAULT_CODECS,
                    "-f",
                    "avi",
                    *FFMPEG_ARGS_DEFAULT_OUTPUT,
                ],
                id="format-user-override",
            ),
            pytest.param(
                {},
                {"copyts": True},
                [
                    *FFMPEG_ARGS_DEFAULT_BASE,
                    *FFMPEG_ARGS_DEFAULT_LOGLEVEL,
                    *FFMPEG_ARGS_DEFAULT_CODECS,
                    "-copyts",
                    *FFMPEG_ARGS_DEFAULT_FORMAT,
                    *FFMPEG_ARGS_DEFAULT_OUTPUT,
                ],
                id="copyts",
            ),
            pytest.param(
                {"ffmpeg-copyts": True},
                {"copyts": False},
                [
                    *FFMPEG_ARGS_DEFAULT_BASE,
                    *FFMPEG_ARGS_DEFAULT_LOGLEVEL,
                    *FFMPEG_ARGS_DEFAULT_CODECS,
                    "-copyts",
                    *FFMPEG_ARGS_DEFAULT_FORMAT,
                    *FFMPEG_ARGS_DEFAULT_OUTPUT,
                ],
                id="copyts-user-override",
            ),
            pytest.param(
                {"ffmpeg-start-at-zero": False},
                {"copyts": True},
                [
                    *FFMPEG_ARGS_DEFAULT_BASE,
                    *FFMPEG_ARGS_DEFAULT_LOGLEVEL,
                    *FFMPEG_ARGS_DEFAULT_CODECS,
                    "-copyts",
                    *FFMPEG_ARGS_DEFAULT_FORMAT,
                    *FFMPEG_ARGS_DEFAULT_OUTPUT,
                ],
                id="copyts-disable-session-start-at-zero",
            ),
            pytest.param(
                {"ffmpeg-copyts": True, "ffmpeg-start-at-zero": False},
                {"copyts": False},
                [
                    *FFMPEG_ARGS_DEFAULT_BASE,
                    *FFMPEG_ARGS_DEFAULT_LOGLEVEL,
                    *FFMPEG_ARGS_DEFAULT_CODECS,
                    "-copyts",
                    *FFMPEG_ARGS_DEFAULT_FORMAT,
                    *FFMPEG_ARGS_DEFAULT_OUTPUT,
                ],
                id="copyts-disable-session-start-at-zero-user-override",
            ),
            pytest.param(
                {"ffmpeg-start-at-zero": True},
                {"copyts": True},
                [
                    *FFMPEG_ARGS_DEFAULT_BASE,
                    *FFMPEG_ARGS_DEFAULT_LOGLEVEL,
                    *FFMPEG_ARGS_DEFAULT_CODECS,
                    "-copyts",
                    "-start_at_zero",
                    *FFMPEG_ARGS_DEFAULT_FORMAT,
                    *FFMPEG_ARGS_DEFAULT_OUTPUT,
                ],
                id="copyts-enable-session-start-at-zero",
            ),
            pytest.param(
                {"ffmpeg-copyts": True, "ffmpeg-start-at-zero": True},
                {"copyts": False},
                [
                    *FFMPEG_ARGS_DEFAULT_BASE,
                    *FFMPEG_ARGS_DEFAULT_LOGLEVEL,
                    *FFMPEG_ARGS_DEFAULT_CODECS,
                    "-copyts",
                    "-start_at_zero",
                    *FFMPEG_ARGS_DEFAULT_FORMAT,
                    *FFMPEG_ARGS_DEFAULT_OUTPUT,
                ],
                id="copyts-enable-session-start-at-zero-user-override",
            ),
            pytest.param(
                {},
                {"copyts": True, "start_at_zero": False},
                [
                    *FFMPEG_ARGS_DEFAULT_BASE,
                    *FFMPEG_ARGS_DEFAULT_LOGLEVEL,
                    *FFMPEG_ARGS_DEFAULT_CODECS,
                    "-copyts",
                    *FFMPEG_ARGS_DEFAULT_FORMAT,
                    *FFMPEG_ARGS_DEFAULT_OUTPUT,
                ],
                id="copyts-disable-start-at-zero",
            ),
            pytest.param(
                {"ffmpeg-copyts": True},
                {"copyts": False, "start_at_zero": False},
                [
                    *FFMPEG_ARGS_DEFAULT_BASE,
                    *FFMPEG_ARGS_DEFAULT_LOGLEVEL,
                    *FFMPEG_ARGS_DEFAULT_CODECS,
                    "-copyts",
                    *FFMPEG_ARGS_DEFAULT_FORMAT,
                    *FFMPEG_ARGS_DEFAULT_OUTPUT,
                ],
                id="copyts-disable-start-at-zero-user-override",
            ),
            pytest.param(
                {},
                {"copyts": True, "start_at_zero": True},
                [
                    *FFMPEG_ARGS_DEFAULT_BASE,
                    *FFMPEG_ARGS_DEFAULT_LOGLEVEL,
                    *FFMPEG_ARGS_DEFAULT_CODECS,
                    "-copyts",
                    "-start_at_zero",
                    *FFMPEG_ARGS_DEFAULT_FORMAT,
                    *FFMPEG_ARGS_DEFAULT_OUTPUT,
                ],
                id="copyts-enable-start-at-zero",
            ),
            pytest.param(
                {"ffmpeg-copyts": True},
                {"copyts": False, "start_at_zero": True},
                [
                    *FFMPEG_ARGS_DEFAULT_BASE,
                    *FFMPEG_ARGS_DEFAULT_LOGLEVEL,
                    *FFMPEG_ARGS_DEFAULT_CODECS,
                    "-copyts",
                    "-start_at_zero",
                    *FFMPEG_ARGS_DEFAULT_FORMAT,
                    *FFMPEG_ARGS_DEFAULT_OUTPUT,
                ],
                id="copyts-enable-start-at-zero-user-override",
            ),
            pytest.param(
                {},
                {"vcodec": "avc"},
                [
                    *FFMPEG_ARGS_DEFAULT_BASE,
                    *FFMPEG_ARGS_DEFAULT_LOGLEVEL,
                    "-c:v",
                    "avc",
                    "-c:a",
                    FFMPEGMuxer.DEFAULT_AUDIO_CODEC,
                    *FFMPEG_ARGS_DEFAULT_FORMAT,
                    *FFMPEG_ARGS_DEFAULT_OUTPUT,
                ],
                id="vcodec",
            ),
            pytest.param(
                {"ffmpeg-video-transcode": "divx"},
                {"vcodec": "avc"},
                [
                    *FFMPEG_ARGS_DEFAULT_BASE,
                    *FFMPEG_ARGS_DEFAULT_LOGLEVEL,
                    "-c:v",
                    "divx",
                    "-c:a",
                    FFMPEGMuxer.DEFAULT_AUDIO_CODEC,
                    *FFMPEG_ARGS_DEFAULT_FORMAT,
                    *FFMPEG_ARGS_DEFAULT_OUTPUT,
                ],
                id="vcodec-user-override",
            ),
            pytest.param(
                {},
                {"acodec": "mp3"},
                [
                    *FFMPEG_ARGS_DEFAULT_BASE,
                    *FFMPEG_ARGS_DEFAULT_LOGLEVEL,
                    "-c:v",
                    FFMPEGMuxer.DEFAULT_VIDEO_CODEC,
                    "-c:a",
                    "mp3",
                    *FFMPEG_ARGS_DEFAULT_FORMAT,
                    *FFMPEG_ARGS_DEFAULT_OUTPUT,
                ],
                id="acodec",
            ),
            pytest.param(
                {"ffmpeg-audio-transcode": "ogg"},
                {"acodec": "mp3"},
                [
                    *FFMPEG_ARGS_DEFAULT_BASE,
                    *FFMPEG_ARGS_DEFAULT_LOGLEVEL,
                    "-c:v",
                    FFMPEGMuxer.DEFAULT_VIDEO_CODEC,
                    "-c:a",
                    "ogg",
                    *FFMPEG_ARGS_DEFAULT_FORMAT,
                    *FFMPEG_ARGS_DEFAULT_OUTPUT,
                ],
                id="acodec-user-override",
            ),
            pytest.param(
                {},
                {"vcodec": "avc", "acodec": "mp3"},
                [
                    *FFMPEG_ARGS_DEFAULT_BASE,
                    *FFMPEG_ARGS_DEFAULT_LOGLEVEL,
                    "-c:v",
                    "avc",
                    "-c:a",
                    "mp3",
                    *FFMPEG_ARGS_DEFAULT_FORMAT,
                    *FFMPEG_ARGS_DEFAULT_OUTPUT,
                ],
                id="vcodec-acodec",
            ),
            pytest.param(
                {"ffmpeg-video-transcode": "divx", "ffmpeg-audio-transcode": "ogg"},
                {"vcodec": "avc", "acodec": "mp3"},
                [
                    *FFMPEG_ARGS_DEFAULT_BASE,
                    *FFMPEG_ARGS_DEFAULT_LOGLEVEL,
                    "-c:v",
                    "divx",
                    "-c:a",
                    "ogg",
                    *FFMPEG_ARGS_DEFAULT_FORMAT,
                    *FFMPEG_ARGS_DEFAULT_OUTPUT,
                ],
                id="vcodec-acodec-user-override",
            ),
            pytest.param(
                {},
                {"maps": ["test", "test2"]},
                [
                    *FFMPEG_ARGS_DEFAULT_BASE,
                    *FFMPEG_ARGS_DEFAULT_LOGLEVEL,
                    *FFMPEG_ARGS_DEFAULT_CODECS,
                    "-map",
                    "test",
                    "-map",
                    "test2",
                    *FFMPEG_ARGS_DEFAULT_FORMAT,
                    *FFMPEG_ARGS_DEFAULT_OUTPUT,
                ],
                id="maps",
            ),
            pytest.param(
                {},
                {"metadata": {"s:a:0": ["language=eng"]}},
                [
                    *FFMPEG_ARGS_DEFAULT_BASE,
                    *FFMPEG_ARGS_DEFAULT_LOGLEVEL,
                    *FFMPEG_ARGS_DEFAULT_CODECS,
                    "-metadata:s:a:0",
                    "language=eng",
                    *FFMPEG_ARGS_DEFAULT_FORMAT,
                    *FFMPEG_ARGS_DEFAULT_OUTPUT,
                ],
                id="metadata-stream-audio",
            ),
            pytest.param(
                {},
                {"metadata": {None: ["title=test"]}},
                [
                    *FFMPEG_ARGS_DEFAULT_BASE,
                    *FFMPEG_ARGS_DEFAULT_LOGLEVEL,
                    *FFMPEG_ARGS_DEFAULT_CODECS,
                    "-metadata",
                    "title=test",
                    *FFMPEG_ARGS_DEFAULT_FORMAT,
                    *FFMPEG_ARGS_DEFAULT_OUTPUT,
                ],
                id="metadata-title",
            ),
        ],
    )
    def test_ffmpeg_args(
        self,
        session: Streamlink,
        popen: Mock,
        options: dict,
        muxer_args: dict,
        expected: list,
    ):
        session.options.update(options)
        streamio = FFMPEGMuxer(session, **muxer_args)

        streamio.open()
        assert popen.call_args_list == [
            call(
                ["ffmpeg", *expected],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            ),
        ]

        streamio.close()

    def test_stderr(self, monkeypatch: pytest.MonkeyPatch, session: Streamlink, popen: Mock):
        mock_stderr = Mock()
        session.options.update({"ffmpeg-verbose": True})
        monkeypatch.setattr("streamlink.stream.ffmpegmux.sys.stderr", mock_stderr)

        streamio = FFMPEGMuxer(session)
        streamio.open()
        assert popen.call_args_list[0][1]["stderr"] is mock_stderr

        streamio.close()
        assert mock_stderr.close.call_count == 0

    @pytest.mark.parametrize(
        ("options", "side_effect"),
        [
            pytest.param({"ffmpeg-verbose-path": "foo"}, None, id="verbose-path"),
            pytest.param({"ffmpeg-verbose-path": "foo", "ffmpeg-verbose": True}, None, id="verbose-path priority"),
            pytest.param({"ffmpeg-verbose-path": "foo"}, OSError, id="OSError on close"),
        ],
    )
    def test_stderr_path(
        self,
        monkeypatch: pytest.MonkeyPatch,
        session: Streamlink,
        popen: Mock,
        options: dict,
        side_effect: type[Exception] | None,
    ):
        mock_path = Mock()
        session.options.update(options)
        monkeypatch.setattr("streamlink.stream.ffmpegmux.Path", mock_path)

        file: Mock = mock_path("foo").expanduser().open("w")
        file.close.side_effect = side_effect
        streamio = FFMPEGMuxer(session)

        streamio.open()
        assert popen.call_args_list[0][1]["stderr"] is file
        assert file.close.call_count == 0

        streamio.close()
        assert file.close.call_count == 1
