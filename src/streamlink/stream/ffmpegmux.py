from __future__ import annotations

import concurrent.futures
import logging
import re
import subprocess
import sys
import threading
from collections.abc import Sequence
from contextlib import suppress
from functools import lru_cache
from pathlib import Path
from shutil import which
from typing import Any, ClassVar, Generic, TextIO, TypeVar

from streamlink import StreamError
from streamlink.stream.stream import Stream, StreamIO
from streamlink.utils.named_pipe import NamedPipe, NamedPipeBase
from streamlink.utils.processoutput import ProcessOutput


log = logging.getLogger(__name__)

_lock_resolve_command = threading.Lock()


TSubstreams = TypeVar("TSubstreams", bound=Stream)


class MuxedStream(Stream, Generic[TSubstreams]):
    """
    Muxes multiple streams into one output stream.
    """

    __shortname__ = "muxed-stream"

    def __init__(
        self,
        session,
        *substreams: TSubstreams,
        **options,
    ):
        """
        :param streamlink.Streamlink session: Streamlink session instance
        :param substreams: Video and/or audio streams
        :param options: Additional keyword arguments passed to :class:`ffmpegmux.FFMPEGMuxer`.
                        Subtitle streams need to be set via the ``subtitles`` keyword.
        """

        super().__init__(session)
        self.substreams: Sequence[TSubstreams] = substreams
        self.subtitles: dict[str, Stream] = options.pop("subtitles", {})
        self.options: dict[str, Any] = options

    def open(self):
        fds = []
        metadata = self.options.get("metadata", {})
        maps = self.options.get("maps", [])
        # only update the maps values if they haven't been set
        update_maps = not maps
        for substream in self.substreams:
            log.debug("Opening {0} substream".format(substream.shortname()))
            if update_maps:
                maps.append(len(fds))
            fds.append(substream and substream.open())

        for i, subtitle in enumerate(self.subtitles.items()):
            language, substream = subtitle
            log.debug("Opening {0} subtitle stream".format(substream.shortname()))
            if update_maps:
                maps.append(len(fds))
            fds.append(substream and substream.open())
            metadata["s:s:{0}".format(i)] = ["language={0}".format(language)]

        self.options["metadata"] = metadata
        self.options["maps"] = maps

        return FFMPEGMuxer(self.session, *fds, **self.options).open()

    @classmethod
    def is_usable(cls, session):
        return FFMPEGMuxer.is_usable(session)


class FFMPEGMuxer(StreamIO):
    __commands__: ClassVar[list[str]] = ["ffmpeg"]

    DEFAULT_LOGLEVEL = "info"
    DEFAULT_OUTPUT_FORMAT = "matroska"
    DEFAULT_VIDEO_CODEC = "copy"
    DEFAULT_AUDIO_CODEC = "copy"

    FFMPEG_VERSION: str | None = None
    FFMPEG_VERSION_TIMEOUT = 4.0

    errorlog: int | TextIO

    @classmethod
    def is_usable(cls, session):
        return cls.command(session) is not None

    @classmethod
    def command(cls, session):
        with _lock_resolve_command:
            return cls._resolve_command(
                session.options.get("ffmpeg-ffmpeg"),
                not session.options.get("ffmpeg-no-validation"),
            )

    @classmethod
    @lru_cache(maxsize=128)
    def _resolve_command(cls, command: str | None = None, validate: bool = True) -> str | None:
        if command:
            resolved = which(command)
        else:
            resolved = None
            for cmd in cls.__commands__:
                resolved = which(cmd)
                if resolved:
                    break

        if resolved and validate:
            log.trace(f"Querying FFmpeg version: {[resolved, '-version']}")  # type: ignore[attr-defined]
            versionoutput = FFmpegVersionOutput([resolved, "-version"], timeout=cls.FFMPEG_VERSION_TIMEOUT)
            if not versionoutput.run():
                log.error("Could not validate FFmpeg!")
                log.error(f"Unexpected FFmpeg version output while running {[resolved, '-version']}")
                resolved = None
            else:
                cls.FFMPEG_VERSION = versionoutput.version
                for i, line in enumerate(versionoutput.output):
                    log.debug(f" {line}" if i > 0 else line)

        if not resolved:
            log.warning("No valid FFmpeg binary was found. See the --ffmpeg-ffmpeg option.")
            log.warning("Muxing streams is unsupported! Only a subset of the available streams can be returned!")

        return resolved

    @staticmethod
    def copy_to_pipe(stream: StreamIO, pipe: NamedPipeBase):
        log.debug(f"Starting copy to pipe: {pipe.path}")
        # TODO: catch OSError when creating/opening pipe fails and close entire output stream
        pipe.open()

        while True:
            try:
                data = stream.read(8192)
            except (OSError, ValueError) as err:
                log.error(f"Error while reading from substream: {err}")
                break

            if data == b"":
                log.debug(f"Pipe copy complete: {pipe.path}")
                break

            try:
                pipe.write(data)
            except OSError as err:
                log.error(f"Error while writing to pipe {pipe.path}: {err}")
                break

        with suppress(OSError):
            pipe.close()

    def __init__(self, session, *streams, **options):
        self.session = session
        self.process = None
        self.errorlog = subprocess.DEVNULL

        if not self.is_usable(session):
            raise StreamError("Cannot use FFmpeg")

        self.streams = streams
        self.pipes = [NamedPipe() for _ in self.streams]
        self.pipe_threads = [
            threading.Thread(
                target=self.copy_to_pipe,
                args=(stream, np),
            )
            for stream, np in zip(self.streams, self.pipes)
        ]

        loglevel = session.options.get("ffmpeg-loglevel") or options.pop("loglevel", self.DEFAULT_LOGLEVEL)
        ofmt = session.options.get("ffmpeg-fout") or options.pop("format", self.DEFAULT_OUTPUT_FORMAT)
        outpath = options.pop("outpath", "pipe:1")
        videocodec = session.options.get("ffmpeg-video-transcode") or options.pop("vcodec", self.DEFAULT_VIDEO_CODEC)
        audiocodec = session.options.get("ffmpeg-audio-transcode") or options.pop("acodec", self.DEFAULT_AUDIO_CODEC)
        metadata = options.pop("metadata", {})
        maps = options.pop("maps", [])
        copyts = session.options.get("ffmpeg-copyts") or options.pop("copyts", False)
        start_at_zero = session.options.get("ffmpeg-start-at-zero") or options.pop("start_at_zero", False)

        self._cmd = [
            self.command(session),
            "-y",
            "-nostats",
            "-loglevel",
            loglevel,
        ]

        for np in self.pipes:
            self._cmd.extend(["-i", str(np.path)])

        self._cmd.extend(["-c:v", videocodec])
        self._cmd.extend(["-c:a", audiocodec])

        for m in maps:
            self._cmd.extend(["-map", str(m)])

        if copyts:
            self._cmd.extend(["-copyts"])
            if start_at_zero:
                self._cmd.extend(["-start_at_zero"])

        for stream, data in metadata.items():
            for datum in data:
                stream_id = ":{0}".format(stream) if stream else ""
                self._cmd.extend(["-metadata{0}".format(stream_id), datum])

        self._cmd.extend(["-f", ofmt, outpath])
        log.debug("ffmpeg command: {0}".format(" ".join(self._cmd)))

        if session.options.get("ffmpeg-verbose-path"):
            self.errorlog = Path(session.options.get("ffmpeg-verbose-path")).expanduser().open("w")
        elif session.options.get("ffmpeg-verbose"):
            self.errorlog = sys.stderr

    def open(self):
        for t in self.pipe_threads:
            t.daemon = True
            t.start()
        self.process = subprocess.Popen(self._cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=self.errorlog)

        return self

    def read(self, size=-1):
        return self.process.stdout.read(size)

    def close(self):
        if self.closed:
            return

        log.debug("Closing ffmpeg thread")
        if self.process:
            # kill ffmpeg
            self.process.kill()
            self.process.stdout.close()

            executor = concurrent.futures.ThreadPoolExecutor()

            # close the substreams
            futures = [
                executor.submit(stream.close)
                for stream in self.streams
                if hasattr(stream, "close") and callable(stream.close)
            ]  # fmt: skip
            concurrent.futures.wait(futures, return_when=concurrent.futures.ALL_COMPLETED)
            log.debug("Closed all the substreams")

            # wait for substream copy-to-pipe threads to terminate and clean up the opened pipes
            timeout = self.session.options.get("stream-timeout")
            futures = [
                executor.submit(thread.join, timeout=timeout)
                for thread in self.pipe_threads
            ]  # fmt: skip
            concurrent.futures.wait(futures, return_when=concurrent.futures.ALL_COMPLETED)

        if self.errorlog is not sys.stderr and self.errorlog is not subprocess.DEVNULL:
            with suppress(OSError):
                self.errorlog.close()

        super().close()


class FFmpegVersionOutput(ProcessOutput):
    # The version output format of the fftools hasn't been changed since n0.7.1 (2011-04-23):
    # https://github.com/FFmpeg/FFmpeg/blame/n5.1.1/fftools/ffmpeg.c#L110
    # https://github.com/FFmpeg/FFmpeg/blame/n5.1.1/fftools/opt_common.c#L201
    # https://github.com/FFmpeg/FFmpeg/blame/c99b93c5d53d8f4a4f1fafc90f3dfc51467ee02e/fftools/cmdutils.c#L1156
    # https://github.com/FFmpeg/FFmpeg/commit/89b503b55f2b2713f1c3cc8981102c1a7b663281
    _re_version = re.compile(r"ffmpeg version (?P<version>\S+)")

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.version: str | None = None
        self.output: list[str] = []

    def onexit(self, code: int) -> bool:
        return code == 0 and self.version is not None

    def onstdout(self, idx: int, line: str) -> bool | None:
        # only validate the very first line of the stdout stream
        if idx == 0:
            match = self._re_version.match(line)
            # abort if the very first line of stdout doesn't match the expected format
            if not match:
                return False
            self.version = match["version"]

        self.output.append(line)
