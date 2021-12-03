import logging
from threading import Event

from requests.exceptions import ChunkedEncodingError, ConnectionError, ContentDecodingError, StreamConsumedError

from streamlink.stream.hls import HLSStreamReader, HLSStreamWriter

log = logging.getLogger(__name__)


class FilteredHLSStreamWriter(HLSStreamWriter):
    def should_filter_sequence(self, sequence):
        return False

    def write(self, sequence, *args, **kwargs):
        if not self.should_filter_sequence(sequence):
            try:
                return super(FilteredHLSStreamWriter, self).write(sequence, *args, **kwargs)
            finally:
                # unblock reader thread after writing data to the buffer
                if not self.reader.filter_event.is_set():
                    log.info("Resuming stream output")
                    self.reader.filter_event.set()
        else:
            self._write_discard(sequence, *args, **kwargs)
            # block reader thread if filtering out segments
            if self.reader.filter_event.is_set():
                log.info("Filtering out segments and pausing stream output")
                self.reader.filter_event.clear()

    def _write_discard(self, sequence, res, chunk_size=8192):
        # The full response needs to actually be read from the socket
        # even if there isn't any intention of using the payload
        try:
            for _ in res.iter_content(chunk_size):
                pass
        except (ChunkedEncodingError, ContentDecodingError, ConnectionError, StreamConsumedError):
            pass


class FilteredHLSStreamReader(HLSStreamReader):
    def __init__(self, *args, **kwargs):
        super(FilteredHLSStreamReader, self).__init__(*args, **kwargs)
        self.filter_event = Event()
        self.filter_event.set()

    def read(self, size):
        while True:
            try:
                return super(FilteredHLSStreamReader, self).read(size)
            except IOError:
                # wait indefinitely until filtering ends
                self.filter_event.wait()
                if self.buffer.closed:
                    return b""
                # if data is available, try reading again
                if self.buffer.length > 0:
                    continue
                # raise if not filtering and no data available
                raise

    def close(self):
        super(FilteredHLSStreamReader, self).close()
        self.filter_event.set()
