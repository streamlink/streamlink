from threading import Event

from streamlink.buffers import Buffer
from streamlink.stream.stream import StreamIO


class FilteredStream(StreamIO):
    """StreamIO mixin for being able to pause read calls while filtering content"""

    buffer: Buffer

    def __init__(self, *args, **kwargs):
        self._event_filter = Event()
        self._event_filter.set()
        super().__init__(*args, **kwargs)

    def read(self, *args, **kwargs) -> bytes:
        read = super().read
        while True:
            try:
                return read(*args, **kwargs)
            except OSError:
                # wait indefinitely until filtering ends
                self._event_filter.wait()
                if self.buffer.closed:
                    return b""
                # if data is available, try reading again
                if self.buffer.length > 0:
                    continue
                # raise if not filtering and no data available
                raise

    def close(self) -> None:
        super().close()
        self._event_filter.set()

    def is_paused(self) -> bool:
        return not self._event_filter.is_set()

    def pause(self) -> None:
        self._event_filter.clear()

    def resume(self) -> None:
        self._event_filter.set()

    def filter_wait(self, timeout=None):
        return self._event_filter.wait(timeout)
