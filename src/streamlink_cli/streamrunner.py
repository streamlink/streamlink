import errno
import logging
import sys
from contextlib import suppress
from pathlib import Path
from threading import Event, Lock, Thread
from typing import Optional

from streamlink.stream.stream import StreamIO
from streamlink_cli.output import FileOutput, HTTPOutput, Output, PlayerOutput
from streamlink_cli.utils.progress import Progress


# Use the main Streamlink CLI module as logger
log = logging.getLogger("streamlink.cli")


ACCEPTABLE_ERRNO = errno.EPIPE, errno.EINVAL, errno.ECONNRESET
with suppress(AttributeError):
    ACCEPTABLE_ERRNO += (errno.WSAECONNABORTED,)  # type: ignore[assignment,attr-defined]


def _noop(_):
    return None


class _ReadError(BaseException):
    pass


class PlayerPollThread(Thread):
    """
    Poll the player process in a separate thread, to isolate it from the stream's read-loop in the main thread.
    Reading the stream can stall indefinitely when filtering content.
    """

    POLLING_INTERVAL: float = 0.5

    def __init__(self, stream: StreamIO, output: PlayerOutput):
        super().__init__(daemon=True, name=self.__class__.__name__)
        self._stream = stream
        self._output = output
        self._stop_polling = Event()
        self._lock = Lock()

    def close(self):
        self._stop_polling.set()

    def playerclosed(self):
        # Ensure that "Player closed" does only get logged once, either when writing the read stream data has failed,
        # or when the player process was terminated/killed before writing.
        with self._lock:
            if self._stop_polling.is_set():
                return
            self.close()
            log.info("Player closed")

    def poll(self) -> bool:
        return self._output.player.poll() is None

    def run(self) -> None:
        while not self._stop_polling.wait(self.POLLING_INTERVAL):
            if self.poll():
                continue
            self.playerclosed()
            # close stream as soon as the player was closed
            self._stream.close()
            break


class StreamRunner:
    """Read data from a stream and write it to the output."""

    playerpoller: Optional[PlayerPollThread] = None
    progress: Optional[Progress] = None

    def __init__(
        self,
        stream: StreamIO,
        output: Output,
        show_progress: bool = False,
    ):
        self.stream = stream
        self.output = output
        self.is_http = isinstance(output, HTTPOutput)

        filename: Optional[Path] = None

        if isinstance(output, PlayerOutput):
            self.playerpoller = PlayerPollThread(stream, output)
            if output.record:
                filename = output.record.filename

        elif isinstance(output, FileOutput):
            if output.filename:
                filename = output.filename
            elif output.record:
                filename = output.record.filename

        if filename and show_progress:
            self.progress = Progress(sys.stderr, filename)

    def run(
        self,
        prebuffer: bytes,
        chunk_size: int = 8192,
    ) -> None:
        read = self.stream.read
        write = self.output.write
        progress = self.progress.write if self.progress else _noop

        if self.playerpoller:
            self.playerpoller.start()
        if self.progress:
            self.progress.start()

        # TODO: Fix error messages (s/when/while/) and only log "Stream ended" when it ended on its own (data == b"").
        #       These are considered breaking changes of the CLI output, which is parsed by 3rd party tools.
        try:
            write(prebuffer)
            progress(prebuffer)
            del prebuffer

            # Don't check for stream.closed, so the buffer's contents can be fully read after the stream ended or was closed
            while True:
                try:
                    data = read(chunk_size)
                    if data == b"":
                        break
                except OSError as err:
                    raise _ReadError() from err

                write(data)
                progress(data)

        except _ReadError as err:
            raise OSError(f"Error when reading from stream: {err.__context__}, exiting") from err.__context__

        except OSError as err:
            if self.playerpoller and err.errno in ACCEPTABLE_ERRNO:
                self.playerpoller.playerclosed()
            elif self.is_http and err.errno in ACCEPTABLE_ERRNO:
                log.info("HTTP connection closed")
            else:
                raise OSError(f"Error when writing to output: {err}, exiting") from err

        finally:
            if self.playerpoller:
                self.playerpoller.close()
                self.playerpoller.join()
            if self.progress:
                self.progress.close()
                self.progress.join()

            self.stream.close()
            log.info("Stream ended")
