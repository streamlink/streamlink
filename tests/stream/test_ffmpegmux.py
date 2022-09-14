import subprocess
from typing import Dict, List, Optional
from unittest.mock import Mock, call, patch

import pytest

from streamlink import Streamlink
from streamlink.stream.ffmpegmux import FFMPEGMuxer


@pytest.fixture(autouse=True)
def resolve_command_cache_clear():
    FFMPEGMuxer.resolve_command.cache_clear()
    yield
    FFMPEGMuxer.resolve_command.cache_clear()


@pytest.fixture
def session():
    with patch("streamlink.session.Streamlink.load_builtin_plugins"):
        yield Streamlink()


class TestCommand:
    def test_cache(self, session: Streamlink):
        with patch("streamlink.stream.ffmpegmux.which", return_value="some_value") as mock:
            assert FFMPEGMuxer.command(session) == "some_value"
            assert FFMPEGMuxer.command(session) == "some_value"
            assert len(mock.call_args_list) == 1
        with patch("streamlink.stream.ffmpegmux.which", return_value="other_value") as mock:
            assert FFMPEGMuxer.command(session) == "some_value"
            assert len(mock.call_args_list) == 0

    @pytest.mark.parametrize("command,which,expected", [
        pytest.param(None, {"ffmpeg": None}, None, id="resolver-negative"),
        pytest.param(None, {"ffmpeg": "ffmpeg"}, "ffmpeg", id="resolver-posix"),
        pytest.param(None, {"ffmpeg": "ffmpeg.exe"}, "ffmpeg.exe", id="resolver-windows"),
        pytest.param("custom", {"ffmpeg": "ffmpeg"}, None, id="custom-negative"),
        pytest.param("custom", {"ffmpeg": "ffmpeg", "custom": "custom"}, "custom", id="custom-positive"),
    ])
    def test_no_cache(self, session: Streamlink, command: Optional[str], which: Dict, expected: Optional[str]):
        session.options.update({"ffmpeg-ffmpeg": command})
        with patch("streamlink.stream.ffmpegmux.which", side_effect=lambda value: which.get(value)):
            assert FFMPEGMuxer.command(session) == expected

    @pytest.mark.parametrize("resolved,expected", [
        pytest.param(None, False, id="negative"),
        pytest.param("ffmpeg", True, id="positive"),
    ])
    def test_is_usable(self, session: Streamlink, resolved: Optional[str], expected: bool):
        with patch("streamlink.stream.ffmpegmux.which", return_value=resolved):
            assert FFMPEGMuxer.is_usable(session) is expected

    def test_log(self, session: Streamlink):
        with patch("streamlink.stream.ffmpegmux.log") as mock_log, \
             patch("streamlink.stream.ffmpegmux.which", return_value=None):
            assert not FFMPEGMuxer.is_usable(session)
            assert mock_log.warning.call_args_list == [
                call("FFmpeg was not found. See the --ffmpeg-ffmpeg option."),
                call("Muxing streams is unsupported! Only a subset of the available streams can be returned!"),
            ]
            assert not FFMPEGMuxer.is_usable(session)
            assert len(mock_log.warning.call_args_list) == 2

    def test_no_log(self, session: Streamlink):
        with patch("streamlink.stream.ffmpegmux.log") as mock_log, \
             patch("streamlink.stream.ffmpegmux.which", return_value="foo"):
            assert FFMPEGMuxer.is_usable(session)
            assert not mock_log.warning.call_args_list


class TestOpen:
    FFMPEG_ARGS_DEFAULT_BASE = ["-nostats", "-y"]
    FFMPEG_ARGS_DEFAULT_CODECS = ["-c:v", FFMPEGMuxer.DEFAULT_VIDEO_CODEC, "-c:a", FFMPEGMuxer.DEFAULT_AUDIO_CODEC]
    FFMPEG_ARGS_DEFAULT_FORMAT = ["-f", FFMPEGMuxer.DEFAULT_OUTPUT_FORMAT]
    FFMPEG_ARGS_DEFAULT_OUTPUT = ["pipe:1"]

    @pytest.fixture(autouse=True)
    def which(self):
        with patch("streamlink.stream.ffmpegmux.which", return_value="ffmpeg") as mock:
            yield mock

    @pytest.fixture(scope="class")
    def devnull(self):
        with patch("streamlink.stream.ffmpegmux.devnull") as mock_devnull:
            yield mock_devnull()

    @pytest.fixture
    def popen(self):
        with patch("subprocess.Popen") as mock:
            yield mock

    @pytest.mark.parametrize("options,muxer_args,expected", [
        pytest.param(
            {},
            {},
            FFMPEG_ARGS_DEFAULT_BASE
            + FFMPEG_ARGS_DEFAULT_CODECS
            + FFMPEG_ARGS_DEFAULT_FORMAT
            + FFMPEG_ARGS_DEFAULT_OUTPUT,
            id="default",
        ),
        pytest.param(
            {},
            {"format": "mpegts"},
            FFMPEG_ARGS_DEFAULT_BASE
            + FFMPEG_ARGS_DEFAULT_CODECS
            + ["-f", "mpegts"]
            + FFMPEG_ARGS_DEFAULT_OUTPUT,
            id="format",
        ),
        pytest.param(
            {"ffmpeg-fout": "avi"},
            {"format": "mpegts"},
            FFMPEG_ARGS_DEFAULT_BASE
            + FFMPEG_ARGS_DEFAULT_CODECS
            + ["-f", "avi"]
            + FFMPEG_ARGS_DEFAULT_OUTPUT,
            id="format-user-override",
        ),
        pytest.param(
            {},
            {"copyts": True},
            FFMPEG_ARGS_DEFAULT_BASE
            + FFMPEG_ARGS_DEFAULT_CODECS
            + ["-copyts"]
            + FFMPEG_ARGS_DEFAULT_FORMAT
            + FFMPEG_ARGS_DEFAULT_OUTPUT,
            id="copyts",
        ),
        pytest.param(
            {"ffmpeg-copyts": True},
            {"copyts": False},
            FFMPEG_ARGS_DEFAULT_BASE
            + FFMPEG_ARGS_DEFAULT_CODECS
            + ["-copyts"]
            + FFMPEG_ARGS_DEFAULT_FORMAT
            + FFMPEG_ARGS_DEFAULT_OUTPUT,
            id="copyts-user-override",
        ),
        pytest.param(
            {"ffmpeg-start-at-zero": False},
            {"copyts": True},
            FFMPEG_ARGS_DEFAULT_BASE
            + FFMPEG_ARGS_DEFAULT_CODECS
            + ["-copyts"]
            + FFMPEG_ARGS_DEFAULT_FORMAT
            + FFMPEG_ARGS_DEFAULT_OUTPUT,
            id="copyts-disable-session-start-at-zero",
        ),
        pytest.param(
            {"ffmpeg-copyts": True, "ffmpeg-start-at-zero": False},
            {"copyts": False},
            FFMPEG_ARGS_DEFAULT_BASE
            + FFMPEG_ARGS_DEFAULT_CODECS
            + ["-copyts"]
            + FFMPEG_ARGS_DEFAULT_FORMAT
            + FFMPEG_ARGS_DEFAULT_OUTPUT,
            id="copyts-disable-session-start-at-zero-user-override",
        ),
        pytest.param(
            {"ffmpeg-start-at-zero": True},
            {"copyts": True},
            FFMPEG_ARGS_DEFAULT_BASE
            + FFMPEG_ARGS_DEFAULT_CODECS
            + ["-copyts", "-start_at_zero"]
            + FFMPEG_ARGS_DEFAULT_FORMAT
            + FFMPEG_ARGS_DEFAULT_OUTPUT,
            id="copyts-enable-session-start-at-zero",
        ),
        pytest.param(
            {"ffmpeg-copyts": True, "ffmpeg-start-at-zero": True},
            {"copyts": False},
            FFMPEG_ARGS_DEFAULT_BASE
            + FFMPEG_ARGS_DEFAULT_CODECS
            + ["-copyts", "-start_at_zero"]
            + FFMPEG_ARGS_DEFAULT_FORMAT
            + FFMPEG_ARGS_DEFAULT_OUTPUT,
            id="copyts-enable-session-start-at-zero-user-override",
        ),
        pytest.param(
            {},
            {"copyts": True, "start_at_zero": False},
            FFMPEG_ARGS_DEFAULT_BASE
            + FFMPEG_ARGS_DEFAULT_CODECS
            + ["-copyts"]
            + FFMPEG_ARGS_DEFAULT_FORMAT
            + FFMPEG_ARGS_DEFAULT_OUTPUT,
            id="copyts-disable-start-at-zero",
        ),
        pytest.param(
            {"ffmpeg-copyts": True},
            {"copyts": False, "start_at_zero": False},
            FFMPEG_ARGS_DEFAULT_BASE
            + FFMPEG_ARGS_DEFAULT_CODECS
            + ["-copyts"]
            + FFMPEG_ARGS_DEFAULT_FORMAT
            + FFMPEG_ARGS_DEFAULT_OUTPUT,
            id="copyts-disable-start-at-zero-user-override",
        ),
        pytest.param(
            {},
            {"copyts": True, "start_at_zero": True},
            FFMPEG_ARGS_DEFAULT_BASE
            + FFMPEG_ARGS_DEFAULT_CODECS
            + ["-copyts", "-start_at_zero"]
            + FFMPEG_ARGS_DEFAULT_FORMAT
            + FFMPEG_ARGS_DEFAULT_OUTPUT,
            id="copyts-enable-start-at-zero",
        ),
        pytest.param(
            {"ffmpeg-copyts": True},
            {"copyts": False, "start_at_zero": True},
            FFMPEG_ARGS_DEFAULT_BASE
            + FFMPEG_ARGS_DEFAULT_CODECS
            + ["-copyts", "-start_at_zero"]
            + FFMPEG_ARGS_DEFAULT_FORMAT
            + FFMPEG_ARGS_DEFAULT_OUTPUT,
            id="copyts-enable-start-at-zero-user-override",
        ),
        pytest.param(
            {},
            {"vcodec": "avc"},
            FFMPEG_ARGS_DEFAULT_BASE
            + ["-c:v", "avc", "-c:a", FFMPEGMuxer.DEFAULT_AUDIO_CODEC]
            + FFMPEG_ARGS_DEFAULT_FORMAT
            + FFMPEG_ARGS_DEFAULT_OUTPUT,
            id="vcodec",
        ),
        pytest.param(
            {"ffmpeg-video-transcode": "divx"},
            {"vcodec": "avc"},
            FFMPEG_ARGS_DEFAULT_BASE
            + ["-c:v", "divx", "-c:a", FFMPEGMuxer.DEFAULT_AUDIO_CODEC]
            + FFMPEG_ARGS_DEFAULT_FORMAT
            + FFMPEG_ARGS_DEFAULT_OUTPUT,
            id="vcodec-user-override",
        ),
        pytest.param(
            {},
            {"acodec": "mp3"},
            FFMPEG_ARGS_DEFAULT_BASE
            + ["-c:v", FFMPEGMuxer.DEFAULT_VIDEO_CODEC, "-c:a", "mp3"]
            + FFMPEG_ARGS_DEFAULT_FORMAT
            + FFMPEG_ARGS_DEFAULT_OUTPUT,
            id="acodec",
        ),
        pytest.param(
            {"ffmpeg-audio-transcode": "ogg"},
            {"acodec": "mp3"},
            FFMPEG_ARGS_DEFAULT_BASE
            + ["-c:v", FFMPEGMuxer.DEFAULT_VIDEO_CODEC, "-c:a", "ogg"]
            + FFMPEG_ARGS_DEFAULT_FORMAT
            + FFMPEG_ARGS_DEFAULT_OUTPUT,
            id="acodec-user-override",
        ),
        pytest.param(
            {},
            {"vcodec": "avc", "acodec": "mp3"},
            FFMPEG_ARGS_DEFAULT_BASE
            + ["-c:v", "avc", "-c:a", "mp3"]
            + FFMPEG_ARGS_DEFAULT_FORMAT
            + FFMPEG_ARGS_DEFAULT_OUTPUT,
            id="vcodec-acodec",
        ),
        pytest.param(
            {"ffmpeg-video-transcode": "divx", "ffmpeg-audio-transcode": "ogg"},
            {"vcodec": "avc", "acodec": "mp3"},
            FFMPEG_ARGS_DEFAULT_BASE
            + ["-c:v", "divx", "-c:a", "ogg"]
            + FFMPEG_ARGS_DEFAULT_FORMAT
            + FFMPEG_ARGS_DEFAULT_OUTPUT,
            id="vcodec-acodec-user-override",
        ),
        pytest.param(
            {},
            {"maps": ["test", "test2"]},
            FFMPEG_ARGS_DEFAULT_BASE
            + FFMPEG_ARGS_DEFAULT_CODECS
            + ["-map", "test", "-map", "test2"]
            + FFMPEG_ARGS_DEFAULT_FORMAT
            + FFMPEG_ARGS_DEFAULT_OUTPUT,
            id="maps",
        ),
        pytest.param(
            {},
            {"metadata": {"s:a:0": ["language=eng"]}},
            FFMPEG_ARGS_DEFAULT_BASE
            + FFMPEG_ARGS_DEFAULT_CODECS
            + ["-metadata:s:a:0", "language=eng"]
            + FFMPEG_ARGS_DEFAULT_FORMAT
            + FFMPEG_ARGS_DEFAULT_OUTPUT,
            id="metadata-stream-audio",
        ),
        pytest.param(
            {},
            {"metadata": {None: ["title=test"]}},
            FFMPEG_ARGS_DEFAULT_BASE
            + FFMPEG_ARGS_DEFAULT_CODECS
            + ["-metadata", "title=test"]
            + FFMPEG_ARGS_DEFAULT_FORMAT
            + FFMPEG_ARGS_DEFAULT_OUTPUT,
            id="metadata-title",
        ),
    ])
    def test_ffmpeg_args(
        self,
        session: Streamlink,
        popen: Mock,
        devnull: Mock,
        options: Dict,
        muxer_args: Dict,
        expected: List,
    ):
        session.options.update(options)
        streamio = FFMPEGMuxer(session, **muxer_args)

        streamio.open()
        assert popen.call_args_list == [call(
            ["ffmpeg"] + expected,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=devnull,
        )]

        streamio.close()
        assert not devnull.close.called

    def test_stderr(self, session: Streamlink, popen: Mock):
        session.options.update({"ffmpeg-verbose": True})
        with patch("streamlink.stream.ffmpegmux.sys.stderr") as mock_stderr:
            streamio = FFMPEGMuxer(session)

            streamio.open()
            assert popen.call_args_list[0][1]["stderr"] is mock_stderr

            streamio.close()
            assert not mock_stderr.close.called

    def test_stderr_path(self, session: Streamlink, popen: Mock):
        session.options.update({"ffmpeg-verbose-path": "foo"})
        with patch("streamlink.stream.ffmpegmux.Path") as mock_path:
            file: Mock = mock_path("foo").expanduser().open("w")
            streamio = FFMPEGMuxer(session)

            streamio.open()
            assert popen.call_args_list[0][1]["stderr"] is file

            streamio.close()
            assert file.close.called
