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
            self._stream.close()
            break

class StreamRunner:
    playerpoller: Optional[PlayerPollThread] = None
    progress: Optional[Progress] = None
    max_size_gb: Optional[float] = None

    def __init__(
        self,
        stream: StreamIO,
        output: Output,
        show_progress: bool = False,
        max_size_gb: Optional[float] = None,  
    ):
        self.stream = stream
        self.output = output
        self.is_http = isinstance(output, HTTPOutput)
        self.max_size_gb = max_size_gb  

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
        total_size_bytes = len(prebuffer)  # 记录已下载的大小
        max_size_bytes = self.max_size_gb * 1024 ** 3 if self.max_size_gb else None

        read = self.stream.read
        write = self.output.write
        progress = self.progress.write if self.progress else _noop

        if self.playerpoller:
            self.playerpoller.start()
        if self.progress:
            self.progress.start()

        try:
            write(prebuffer)
            progress(prebuffer)

            while True:
                data = read(chunk_size)
                if data == b"":
                    break

                if max_size_bytes and total_size_bytes + len(data) > max_size_bytes:
                    log.warning(f"Max video size of {self.max_size_gb}GB exceeded, stopping download")
                    #print(f"Max video size of {self.max_size_gb}GB exceeded, stopping download")
                    break  

                write(data)
                progress(data)
                total_size_bytes += len(data)  

        except (OSError, _ReadError) as err:
            log.error(f"Error occurred: {err}")
        finally:
            if self.playerpoller:
                self.playerpoller.close()
                self.playerpoller.join()
            if self.progress:
                self.progress.close()
                self.progress.join()
            self.stream.close()
            log.info("Stream ended")
