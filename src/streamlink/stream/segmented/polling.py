from __future__ import annotations

import abc
import logging
from datetime import datetime, timedelta

from streamlink.exceptions import StreamError
from streamlink.stream.segmented.segmented import SegmentedStreamWorker, TResult, TSegment
from streamlink.utils.times import now


log = logging.getLogger(__name__)


class PollingSegmentedStreamWorker(SegmentedStreamWorker[TSegment, TResult], metaclass=abc.ABCMeta):
    """StreamWorker to be used in segmented streams where new data has to be fetched and processed periodically"""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        dt_now = now()

        self._reload_time: float = 6
        self._reload_last: datetime = dt_now

    @abc.abstractmethod
    def reload(self) -> None:  # pragma: no cover
        """Fetch new data and process it"""
        raise NotImplementedError

    def wait_and_reload(self):
        """Pause the worker until the next reload time interval has been reached, then call reload()"""

        # Exclude fetch+processing time from the overall reload time and reload in a strict time interval
        time_completed = now()
        time_elapsed = max(0.0, (time_completed - self._reload_last).total_seconds())
        time_wait = max(0.0, self._reload_time - time_elapsed)
        if self.wait(time_wait):
            if time_wait > 0:
                # If we had to wait, then don't call now() twice and instead reference the timestamp from before
                # the wait() call, to prevent a shifting time offset due to the execution time
                self._reload_last = time_completed + timedelta(seconds=time_wait)
            else:
                # Otherwise, get the current time, as the reload interval already has shifted
                self._reload_last = now()

            try:
                self.reload()
            except StreamError as err:
                log.warning(f"Reloading failed: {err}")
