import logging
from threading import Event

from streamlink.stream.hls import HLSStreamReader, HLSStreamWriter

log = logging.getLogger(__name__)


class FilteredHLSStreamWriter(HLSStreamWriter):
    def should_filter_sequence(self, sequence):
        return False

    def write(self, sequence, result, *data):
        if not self.should_filter_sequence(sequence):
            try:
                return super(FilteredHLSStreamWriter, self).write(sequence, result, *data)
            finally:
                # unblock reader thread after writing data to the buffer
                if not self.reader.filter_event.is_set():
                    log.info("Resuming stream output")
                    self.reader.filter_event.set()
        else:
            # Read and discard any remaining HTTP response data in the response connection.
            # Unread data in the HTTPResponse connection blocks the connection from being released back to the pool.
            result.raw.drain_conn()

            # block reader thread if filtering out segments
            if self.reader.filter_event.is_set():
                log.info("Filtering out segments and pausing stream output")
                self.reader.filter_event.clear()


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
